import configparser, random, json
from pymongo import MongoClient
from pymongo.collection import Collection
from typing import List, Dict, Any
from datetime import datetime, timezone
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.prompts import K_SEARCH_PROMPT
from utils.llm_utils import call_llm

class MemoryManager:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        mongo_uri = config.get("DB_DETAILS", "uri")
        db_name = config.get("DB_DETAILS", "db")

        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

    def _remove_meta_fields(self, doc: dict) -> dict:
        """Remove metadata fields (_id and timestamp) for comparison."""
        return {k: v for k, v in doc.items() if k not in ["_id", "timestamp"]}

    def _questions_equal(self, q1: dict, q2: dict) -> bool:
        return q1 == q2

    def save_memory_content(
        self,
        user_id: str,
        agent: str,
        doc_hashes: List[str],
        processed_params: Dict[str, Any],
        provided_response: Dict[str, Any]
    ) -> Dict[str, Any]:

        collection: Collection = self.db[user_id]

        # Build response_obj based on agent type
        if agent.lower() == "faq_generator":
            response_obj = {
                "agent": agent,
                "doc_hashes": doc_hashes,
                "parameters": processed_params,
                "questions": provided_response.get("questions", []),
                "timestamp": datetime.now(timezone.utc)
            }

        elif agent.lower() == "summariser":
            response_obj = {
                "agent": agent,
                "doc_hashes": doc_hashes,
                "summary": provided_response.get("summary", ""),
                "compression_ratio": processed_params.get("compression_ratio"),
                "focus_areas": processed_params.get("focus_areas", []),
                "timestamp": datetime.now(timezone.utc)
            }

        elif agent.lower() == "k_search":
            response_obj = {
                "agent": agent,
                "doc_hashes": doc_hashes,
                "response": provided_response.get("response", ""),
                "sources": processed_params.get("sources"),
                "query_text": processed_params.get("query_text"),
                "timestamp": datetime.now(timezone.utc)
            }

        elif agent.lower() == "doc_extractor":
            response_obj = {
                "agent": agent,
                "doc_hashes": doc_hashes,
                "entity_table": provided_response.get("entity_table", []),
                "timestamp": datetime.now(timezone.utc)
            }

        else:
            raise ValueError(f"Unsupported agent type: {agent}")

        # Check for full duplication (ignoring _id and timestamp)
        all_docs = list(collection.find({"agent": agent}))
        for doc in all_docs:
            if self._remove_meta_fields(doc) == self._remove_meta_fields(response_obj):
                return "Not re-inserted since duplicate found"

        # FAQ-specific logic for updating if primary keys match but content differs
        if agent.lower() == "faq_generator":
            existing_doc = collection.find_one({
                "agent": agent,
                "doc_hashes": doc_hashes,
                "parameters": processed_params
            })

            if existing_doc:
                # Only add non-duplicate questions
                existing_questions = existing_doc.get("questions", [])
                new_questions = response_obj["questions"]

                unique_new_questions = [
                    q for q in new_questions if all(not self._questions_equal(q, eq) for eq in existing_questions)
                ]

                if unique_new_questions:
                    collection.update_one(
                        {"_id": existing_doc["_id"]},
                        {"$push": {"questions": {"$each": unique_new_questions}}}
                    )
                    return f"Updated existing FAQ memory with {len(unique_new_questions)} new question(s)."

                else:
                    return "No new questions to add to existing FAQ memory."
        
        # Doc Extractor logic: merge entities if primary keys match (agent + doc_hashes)
        if agent.lower() == "doc_extractor":
            existing_doc = collection.find_one({
                "agent": agent,
                "doc_hashes": doc_hashes
            })

            if existing_doc:
                existing_table = existing_doc.get("entity_table", [])
                new_table = response_obj["entity_table"]

                updated_table_map = {
                    entry["entity_type"].strip().lower(): set(entry.get("values", []))
                    for entry in existing_table
                }

                # Merge logic
                for entry in new_table:
                    etype = entry["entity_type"].strip().lower()
                    new_values = set(entry.get("values", []))

                    if etype in updated_table_map:
                        updated_table_map[etype].update(new_values)
                    else:
                        updated_table_map[etype] = new_values

                # Reconstruct entity_table with no duplicates
                merged_entity_table = [
                    {
                        "entity_type": etype,
                        "values": sorted(list(values))  # Optional: sorted for consistency
                    }
                    for etype, values in updated_table_map.items()
                ]

                collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": {"entity_table": merged_entity_table}}
                )
                return f"Updated existing Doc Extractor memory with merged entity data."

        # Insert new entry if not duplicate or not updatable
        result = collection.insert_one(response_obj)
        return f"Inserted object with ID: {str(result.inserted_id)}"

    def get_memory_content(
        self,
        user_id: str,
        agent: str,
        doc_hashes: List[str],
        processed_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        collection = self.db[user_id]
        if agent.lower().startswith("faq"):
            focus_areas = processed_params.get("focus_areas", [])
            total_required = processed_params.get("question_count", 0)

            # Normalize focus area input
            if not focus_areas:
                focus_areas = [""]  # target blank focus area questions only

            # Find memory entries with overlapping document hashes
            matched_docs = list(collection.find({
                "agent": agent,
                "doc_hashes": {"$in": doc_hashes}
            }))

            # Flatten all questions from matched docs
            all_questions = []
            for doc in matched_docs:
                all_questions.extend(doc.get("questions", []))

            # Bucket questions by focus area
            focus_area_buckets = defaultdict(list)
            for q in all_questions:
                fa = q.get("focus_area", "").strip().lower()
                for req_focus in focus_areas:
                    if fa == req_focus.lower():
                        focus_area_buckets[req_focus].append(q)

            # Randomly distribute odd remainder
            per_focus_required = total_required // len(focus_areas)
            remainder = total_required % len(focus_areas)
            indices = list(range(len(focus_areas)))
            random.shuffle(indices)
            split_map = {
                fa: per_focus_required + (1 if idx in indices[:remainder] else 0)
                for idx, fa in enumerate(focus_areas)
            }

            selected_questions = []
            processing_plan = []

            for fa in focus_areas:
                needed = split_map[fa]
                matched = focus_area_buckets.get(fa, [])

                if len(matched) >= needed:
                    matched_sorted = sorted(
                        matched, key=lambda q: (q.get("rank", 1000), random.random())
                    )
                    selected_questions.extend(matched_sorted[:needed])
                else:
                    if matched:
                        matched_sorted = sorted(
                            matched, key=lambda q: (q.get("rank", 1000), random.random())
                        )
                        selected_questions.extend(matched_sorted)
                    processing_plan.append({
                        "focus_areas": [fa],
                        "question_count": needed - len(matched)
                    })

            # Final reranking of selected questions
            if selected_questions:
                final_sorted = sorted(selected_questions, key=lambda q: (q.get("rank", 1000), random.random()))
                for idx, q in enumerate(final_sorted, start=1):
                    q["rank"] = idx
            else:
                final_sorted = []

            # Decide i_check_result
            if not final_sorted:
                i_check_result = "No Match"
                memory_content = {}
                processing_content = [
                    {
                        "focus_areas": [fa],
                        "question_count": split_map[fa]
                    } for fa in focus_areas
                ]

            elif not processing_plan:
                i_check_result = "Full Match"
                memory_content = {
                    "questions": final_sorted
                }
                processing_content = {}

            else:
                i_check_result = "Partial Match"
                memory_content = {
                    "questions": final_sorted
                }
                processing_content = processing_plan

            return {
                "i_check_result": i_check_result,
                "memory_content": memory_content,
                "processing_content": processing_content
            }
        elif agent.lower().startswith("summariser"):
            requested_ratio = processed_params.get("compression_ratio")
            focus_areas = processed_params.get("focus_areas", [])
            focus_areas_key = focus_areas if focus_areas else []

            # Match only documents with exact doc_hashes and focus_areas
            matched_doc = collection.find_one({
                "agent": "summariser",
                "doc_hashes": {"$all": doc_hashes, "$size": len(doc_hashes)},
                "focus_areas": {"$all": focus_areas_key, "$size": len(focus_areas_key)}
            })

            if not matched_doc:
                return {
                    "i_check_result": "No Match",
                    "memory_content": {},
                    "processing_content": {
                        "focus_areas": focus_areas_key,
                        "compression_ratio": requested_ratio
                    }
                }

            stored_ratio = int(matched_doc.get("compression_ratio"))
            stored_summary = matched_doc.get("summary", "")

            if stored_ratio == requested_ratio:
                return {
                    "i_check_result": "Full Match",
                    "memory_content": {
                        "summary": stored_summary,
                        "compression_ratio": stored_ratio,
                        "focus_areas": focus_areas_key
                    },
                    "processing_content": {}
                }

            elif stored_ratio < requested_ratio:
                # Stored summary is less compressed (longer), we can compress it further
                new_ratio = round(
                    100 * (
                        1 - ((1 - requested_ratio / 100) / (1 - stored_ratio / 100))
                    )
                )

                return {
                    "i_check_result": "Partial Match",
                    "memory_content": {
                        "summary": stored_summary
                    },
                    "processing_content": {
                        "focus_areas": focus_areas_key,
                        "compression_ratio": new_ratio
                    }
                }
            else:
                    return {
                        "i_check_result": "No Match",
                        "memory_content": {},
                        "processing_content": {
                            "focus_areas": focus_areas_key,
                            "compression_ratio": requested_ratio
                        }
                    }
            
        elif agent.lower().startswith("k_search"):
            query_text = processed_params.get("query_text", "").strip().lower()
            sources_required = processed_params.get("sources")

            if not query_text:
                raise ValueError("Missing 'query_text' in parameters for k_search")

            matched_docs = list(collection.find({
                "agent": agent,
                "doc_hashes": {"$in": doc_hashes}
            }))

            qas = []
            for doc in matched_docs:
                qas.append({
                    "query_text": doc.get("query_text", ""),
                    "response": doc.get("response", ""),
                    "sources": doc.get("sources", "")  
                })

            # Exact match check — question and sources count must match
            for qa in qas:
                if (
                    query_text == qa["query_text"].strip().lower()
                    and sources_required is not None
                    and (qa["sources"].lower().strip()) == (sources_required.lower().strip())
                ):
                    return {
                        "i_check_result": "Full Match",
                        "memory_content": {
                            "response": qa["response"]
                        },
                        "processing_content": {}
                    }

            # Fast semantic search using TF-IDF
            corpus = [qa["query_text"] for qa in qas]
            tfidf = TfidfVectorizer().fit(corpus + [query_text])
            vecs = tfidf.transform(corpus)
            query_vec = tfidf.transform([query_text])
            sims = cosine_similarity(query_vec, vecs).flatten()
            top_indices = sims.argsort()[-10:][::-1]

            relevant_qas = [qas[i] for i in top_indices if sims[i] > 0.1]
            print(f"Found relevant QAs based on semantic search: {(relevant_qas)}")
            if not relevant_qas:
                return {
                    "i_check_result": "No Match",
                    "memory_content": {},
                    "processing_content": processed_params
                }

            # Build structured LLM prompt
            context_parts = []
            for i, qa in enumerate(relevant_qas):
                context_parts.append(f"Q{i+1}: {qa['query_text']}\nA{i+1}: {qa['response']}")
            context_text = "\n\n".join(context_parts)

            prompt = K_SEARCH_PROMPT.format(
                user_query=query_text,
                context_text=context_text
            )

            llm_response = call_llm(prompt).strip()
            try:
                parsed = json.loads(llm_response)
                if parsed.get("answerable") is True and parsed.get("answer"):
                    return {
                        "i_check_result": "Partial Match",
                        "memory_content": {
                            "response": parsed["answer"]
                        },
                        "processing_content": {}
                    }
                else:
                    raise ValueError
            except Exception:
                return {
                    "i_check_result": "No Match",
                    "memory_content": {},
                    "processing_content": processed_params
                }
            
        elif agent.lower().startswith("doc_extractor"):
            requested_entities = processed_params.get("entity_list", [])

            # Find memory doc with exact doc_hashes
            matched_doc = collection.find_one({
                "agent": "doc_extractor",
                "doc_hashes": {"$all": doc_hashes, "$size": len(doc_hashes)}
            })

            if not matched_doc:
                return {
                    "i_check_result": "No Match",
                    "memory_content": {},
                    "processing_content": {
                        "entity_list": requested_entities
                    }
                }

            entity_table = matched_doc.get("entity_table", [])
            entity_map = {
                entry["entity_type"].strip().lower(): entry.get("values", [])
                for entry in entity_table
            }

            matched = {}
            missing = []

            for entity in requested_entities:
                key = entity.strip().lower()
                if key in entity_map:
                    matched[entity] = entity_map[key]
                else:
                    missing.append(entity)

            if not matched:
                i_check_result = "No Match"
                memory_content = {}
                processing_content = {
                    "entity_list": requested_entities
                }
            elif not missing:
                i_check_result = "Full Match"
                memory_content = {
                    "entity_table": [
                        {
                            "entity_type": et,
                            "values": matched[et]
                        } for et in requested_entities
                    ]
                }
                processing_content = {}
            else:
                i_check_result = "Partial Match"
                memory_content = {
                    "entity_table": [
                        {
                            "entity_type": et,
                            "values": matched[et]
                        } for et in matched
                    ]
                }
                processing_content = {
                    "entity_list": missing
                }

            return {
                "i_check_result": i_check_result,
                "memory_content": memory_content,
                "processing_content": processing_content
            }

        else:
            raise ValueError(f"Unsupported agent: {agent}")