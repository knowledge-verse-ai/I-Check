# I-Check
An idempotence optimising framework for saving enterprise resources. This repo hosts the code for I-check with memory included: hosts a modular FastAPI backend that supports multiple intelligent agents with memory optimisation for cost and token savings. It uses document fingerprinting, hashing, and structured matching to avoid redundant LLM invocations.

<img width="2886" height="2196" alt="I-Check_Working" src="https://github.com/user-attachments/assets/9b34000d-4f5e-465d-92e7-4b889662e66c" />


---

## 1. Setup Instructions

```bash
# Step 1: Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Step 2: Install dependencies
pip install -r requirements.txt


# Step 3: Before running the server, create a `config.ini` file in the project root directory with the following structure:

[API_KEYS]
OPENAI_API_KEY = your_openai_api_key_here

[AWS]
aws_region = your_aws_region
aws_access_key_id = your_aws_access_key_id
aws_secret_access_key = your_aws_secret_access_key

[DB_DETAILS]
uri = your_mongodb_uri
db = your_database_name

# Step 3: Run the FastAPI server
python main.py


```

---

## 2. Supported Agents

- **FAQ Generator**
- **Summariser**
- **K_Search (Knowledge Search)**
- **Doc-Extractor**

---

## 3. Usage Instructions

To ensure memory-based optimisation works as intended:

- **Before calling any agent**, call `get_memory` with required parameters. This returns whether a full, partial, or no match is found in memory.
- **After getting a response from the agent**, call `save_memory` to store the result in memory for future reuse.

Refer to this document for agent-wise details with examples: [Implementation Doc](https://docs.google.com/document/d/1R79uE1bl6KHH0mdcNlHp9thym12IZLbaoeuN6QleucM/edit?usp=sharing)

---

## 4. High-Level Agent Logic

Each agent uses hierarchical memory checks based on the document hashes and specific agent parameters.

### FAQ Generator

- **Full Match:** All focus areas covered with the required number of questions
- **Partial Match:** Fewer questions found for one or more focus areas
- **No Match:** No relevant questions found

### Summariser

- **Full Match:** Summary exists with exact focus areas and compression ratio
- **Partial Match:** Same focus areas but with a higher compression ratio; can be reused
- **No Match:** No relevant summary found

### K_Search

- **Full Match:** Exact query text and sources found
- **Partial Match:** Semantically similar queries found and reused
- **No Match:** No similar or exact queries found

### Doc-Extractor

- **Full Match:** All requested entity types found
- **Partial Match:** Some entity types found
- **No Match:** No matching entity types found

---

## 5. Optimisation Key and Impact

Each agent response includes an optional `optimisation` key if memory reuse was applied. This helps track cost and token savings.

### Example: Full Match

```json
"optimisation": {
    "original_tokens": 45539,
    "saved_tokens": 45539,
    "percent_saving_tokens": 100.0,
    "original_cost": 0.2163,
    "saved_cost": 0.2163,
    "percent_saving_cost": 100.0
}
```

**Impact:** The full agent response was reused from memory. No new tokens or cost were incurred.

---

### Example: Partial Match

```json
"optimisation": {
    "original_tokens": 45539,
    "saved_tokens": 15179.67,
    "percent_saving_tokens": 33.33,
    "original_cost": 0.2163,
    "saved_cost": 0.0721,
    "percent_saving_cost": 33.34
}
```

**Impact:** Only a portion of the task was computed again; memory reuse covered the rest, resulting in significant savings.

---


