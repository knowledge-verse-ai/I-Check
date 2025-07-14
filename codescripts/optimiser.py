import tiktoken
import math
from typing import Dict, Any, List
from utils.agent_prompts import *  
from utils.model_prices import MODEL_PRICING 

class Optimiser:
    def __init__(self, model_name: str, agent: str, doc_content: str):
        self.model_name = model_name
        self.agent = agent.lower()
        self.doc_content = doc_content
        self.tokenizer = self._get_tokenizer(model_name)
        self.prompt_tokens = self._compute_prompt_tokens()
        self.chunk_size = self._resolve_chunk_size()

    def _get_tokenizer(self, model_name: str):
        if model_name.lower().startswith("gpt"):
            return lambda text: len(tiktoken.encoding_for_model(model_name).encode(text))
        else:
            # Fallback: assume ~4 chars per token as heuristic
            return lambda text: max(1, len(text) // 4)

    def _resolve_chunk_size(self):
        if "gpt" in self.model_name:
            return 12000 if "3" in self.model_name else 45000
        elif "mistral" in self.model_name:
            return 12000 if "7" in self.model_name else 45000
        elif "llama" in self.model_name:
            return 30000
        else:
            return 45000

    def _compute_prompt_tokens(self) -> Dict[str, int]:
        def tokens(text):
            return self.tokenizer(text)

        return {
            "faq_plain": tokens(FAQS_WITHOUT_FOCUS),
            "faq_focus": tokens(EXTRACT_RELEVANT_TEXT_PROMPT) + tokens(FAQS_WITH_FOCUS),
            "summary_plain": tokens(SUMMARY_PROMPT_WITHOUT_FOCUS),
            "summary_focus": tokens(SUMMARY_PROMPT_WITH_FOCUS),
            "doc_extractor": tokens(DOC_EXTRACTOR_PROMPT),
            "k_search": tokens(K_SEARCH_TEMPLATE) 
        }

    def compute(self, processing_content: Any, memory_content: Any, params:dict,  i_check_result: str =None) -> Dict[str, Any]:
        total_doc_tokens = self.tokenizer(self.doc_content)
        num_chunks = math.ceil(total_doc_tokens / self.chunk_size)
        prices = MODEL_PRICING[self.model_name]

        if self.agent == "faq_generator":
            return self._faq_metrics(processing_content, memory_content, num_chunks, total_doc_tokens, params, prices)
        elif self.agent == "summariser":
            return self._summary_metrics(processing_content, memory_content, num_chunks, total_doc_tokens, params, prices)
        elif self.agent == "k_search":
            return self._ksearch_metrics(processing_content, memory_content, total_doc_tokens, prices, i_check_result)
        elif self.agent == "doc_extractor":
            return self._doc_extractor_metrics(processing_content, memory_content, num_chunks, total_doc_tokens, prices)
        else:
            return {}

    def _faq_metrics(self, processing_content, memory_content, num_chunks, total_tokens, params, prices):
        original_focus_areas = len(params.get("focus_areas", []))
        original_question_count = params.get("question_count", 0)
        print(f"Original Focus Areas: {original_focus_areas}, Original Question Count: {original_question_count}")
        focus = bool(original_focus_areas and original_focus_areas > 0)
        prompt_cost = self.prompt_tokens["faq_focus"] if focus else self.prompt_tokens["faq_plain"]
        
        orig_tokens = num_chunks * (self.chunk_size + prompt_cost)
        required_question_count = 0
        for area in processing_content:
            required_question_count += area.get("question_count", 0)
        if processing_content and memory_content:
            saved_tokens = ((original_question_count - required_question_count) / (original_question_count)) * orig_tokens
        elif memory_content:
            saved_tokens = orig_tokens
        else:
            saved_tokens = 0

        return self._finalise_metrics(orig_tokens, saved_tokens, prices)

    def _summary_metrics(self, processing_content, memory_content, num_chunks, total_tokens, params, prices):
        orig_focus_areas = len(params.get("focus_areas", []))
        focus = bool(orig_focus_areas and orig_focus_areas > 0)
        prompt_cost = self.prompt_tokens["summary_focus"] if focus else self.prompt_tokens["summary_plain"]
        orig_tokens = num_chunks * (self.chunk_size + prompt_cost)

        if processing_content and memory_content:
            summary_ratio = processing_content.get("compression_ratio", 100)
            saved_tokens = orig_tokens * (1 - (summary_ratio / 100))
        elif memory_content:
            saved_tokens = orig_tokens
        else:
            saved_tokens = 0

        return self._finalise_metrics(orig_tokens, saved_tokens, prices)

    def _doc_extractor_metrics(self, processing_content, memory_content, num_chunks, total_tokens, prices):
        entity_count = len(processing_content.get("entity_list", [])) if processing_content else 0
        matched_entity_count = len(memory_content.get("entity_table", [])) if memory_content else 0 
        print(f"Entity Count: {entity_count}, Matched Entity Count: {matched_entity_count}")
        orig_tokens = num_chunks * self.prompt_tokens["doc_extractor"] * (entity_count+matched_entity_count) + total_tokens

        if processing_content and memory_content:
            saved_tokens = (num_chunks * self.prompt_tokens["doc_extractor"] * matched_entity_count) + (total_tokens* matched_entity_count // (matched_entity_count+entity_count))
        elif memory_content:
            saved_tokens = orig_tokens
        else:
            saved_tokens = 0

        return self._finalise_metrics(orig_tokens, saved_tokens, prices)

    def _ksearch_metrics(self, processing_content, memory_content, num_chunks, prices,  i_check_result):
        # Assume 10 retrieved vectors, 1 final prompt
        orig_tokens = (num_chunks * self.prompt_tokens["k_search"] // 100) + self.prompt_tokens["k_search"] * 10
        if i_check_result == "Partial Match":
            saved_tokens = orig_tokens - self.prompt_tokens["k_search"] * 10
        elif i_check_result == "Full Match":
            saved_tokens = orig_tokens
        else:
            saved_tokens = 0
        return self._finalise_metrics(orig_tokens, saved_tokens, prices)

    def _finalise_metrics(self, orig_tokens, saved_tokens, prices):
        orig_cost = self._estimate_cost(orig_tokens, prices)
        saved_cost = self._estimate_cost(saved_tokens, prices)
        return {
            "original_tokens": orig_tokens,
            "saved_tokens": saved_tokens,
            "percent_saving_tokens": round(100 * saved_tokens / orig_tokens, 2) if orig_tokens else 0,
            "original_cost": round(orig_cost, 4),
            "saved_cost": round(saved_cost, 4),
            "percent_saving_cost": round(100 * saved_cost / orig_cost, 2) if orig_cost else 0
        }

    def _estimate_cost(self, tokens, prices):
        input_tokens = int(tokens * 0.7)
        output_tokens = tokens - input_tokens
        return (input_tokens / 1_000_000) * prices["input"] + (output_tokens / 1_000_000) * prices["output"]
