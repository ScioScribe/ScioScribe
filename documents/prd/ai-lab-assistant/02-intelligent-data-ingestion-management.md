# Sub-PRD 2: Intelligent Data Ingestion & Management

**Owner:** Developer 2 (The Engineer)
**Epic:** The Data Steward
**Goal:** To build the backend foundation for getting data into ScioScribe efficiently and ensuring it is clean, secure, and analysis-ready.

## 1. Feature Overview & "Cursor-like" Philosophy

This module handles all aspects of data input. It moves beyond simple file uploads by incorporating AI to structure messy, real-world data from various sources. The core philosophy is to act as an **intelligent co-pilot for data preparation**, much like Cursor assists with code. The system should proactively identify issues, suggest intelligent fixes, and automate tedious transformations, all while keeping the user in full control for verification.

## 2. Role in the ScioScribe Ecosystem

This module is the critical bridge between **Component 1 (Planning)** and **Component 3 (Analysis)**.

* **As a Complementary Module:** It consumes the `ExperimentID` from the planning phase to contextualize the data. It then produces a clean, structured dataset (a "Data Artifact") that is the required input for the analysis engine. Its primary role is to ensure the data passed to Component 3 is of the highest possible quality.
* **As a Standalone Utility:** The features within this module are independently valuable. A user could bypass the formal planning phase and use the "Screenshot-to-CSV" or "Voice-to-Table" features as powerful one-off tools to quickly digitize data, making this component a valuable standalone product.

## 3. Detailed User Flow

1.  **Initiate Upload:** From the project dashboard, the user clicks "Add Data." They are presented with options: "Upload File," "Transcribe Audio," or "Extract from Image."
2.  **File Upload & Initial Processing:**
    * The user uploads a file (CSV, XLSX, image, audio).
    * The backend immediately creates a "Data Artifact" record in Firestore with a status of `processing`.
    * The file is securely uploaded to a private folder in Firebase Storage.
3.  **AI Co-pilot Analysis:**
    * A background job is triggered. The AI scans the data for issues: inconsistent categorical values, potential data type mismatches (e.g., numbers stored as text), outliers, and missing value patterns.
    * The results of this scan are saved to the Data Artifact record. The status changes to `pending_review`.
4.  **Interactive Review & Verification:**
    * The UI notifies the user: "Your data is ready for review."
    * The user sees the data in a spreadsheet view, with problematic cells or columns highlighted.
    * AI suggestions appear in a side panel (e.g., "Standardize 5 unique values in 'Region' column to 'USA'?", "Column 'Age' looks like numbers but is stored as text. Convert?").
    * The user can accept, reject, or modify each suggestion. Each action triggers an API call to update the data.
    * The user can also add free-form qualitative notes in a dedicated text area.
5.  **Finalize:** Once the user approves the changes and adds any notes, they click "Finalize." The backend creates a final, cleaned version of the data file. The Data Artifact status is updated to `ready_for_analysis`.

## 4. Backend Architecture & Data Flow

1.  **Client (React) -> API (FastAPI):** User uploads a file. The request hits the `/upload-file` endpoint.
2.  **API -> Storage (Firebase):** The FastAPI server streams the file directly to a secure, private location in Firebase Storage, named with a unique UUID. This avoids loading large files into server memory.
3.  **API -> Database (Firestore):** The API creates a document in the `data_artifacts` collection. This document contains metadata: `artifactId`, `experimentId`, `originalFileName`, `storagePath`, `status: 'processing'`, `ownerId`.
4.  **API -> Background Task Queue (e.g., Celery/Redis or FastAPI's BackgroundTasks):** The data processing is too slow for a synchronous API response. The API pushes a job to a background queue with the `artifactId`.
5.  **Background Worker -> AI Logic:**
    * The worker retrieves the file from Firebase Storage.
    * It executes the AI analysis pipeline (see Section 11).
    * It updates the Firestore document with the `suggestions` array and sets `status: 'pending_review'`.
6.  **Client -> Database (Real-time):** The frontend has a real-time listener (onSnapshot) attached to the Firestore document. When the status changes to `pending_review`, the UI automatically updates to show the user their data is ready for review.
7.  **Client -> API (for cleaning & notes):** As the user accepts/rejects suggestions or types in the notes field, the frontend calls the relevant endpoints (`/apply-suggestion`, `/update-notes`) to persist the changes.
8.  **Finalization:** The "Finalize" button calls `/finalize-data`, which sets the status to `ready_for_analysis`, making it visible to Component 3.

## 5. Functional Requirements (Backend Focus)

* **FastAPI Endpoints:**
    * `POST /upload-file`: Accepts a file, creates the Firestore record, and queues a processing job. Returns the `artifactId`.
    * `GET /data-artifact/{artifact_id}`: Retrieves the current state of a data artifact, including suggestions and notes.
    * `POST /apply-suggestion`: Applies a specific cleaning suggestion to the data.
    * `POST /update-notes`: Saves or updates the free-form text notes for a given artifact.
    * `POST /finalize-data/{artifact_id}`: Finalizes the data and sets its status to `ready_for_analysis`.
* **Data Processing Logic:** The backend must contain modular Python scripts for:
    * Reading different file types (CSV, XLSX).
    * Interfacing with transcription and OCR models.
    * Detecting data quality issues (type inference, value inconsistency).
    * Applying data transformations based on user approval.
    * Storing and retrieving qualitative text notes associated with a data artifact.

## 6. Expanded Error Handling & Edge Cases

* **File Format & Content:**
    * **Incorrect Delimiter/Encoding:** The backend should handle these gracefully. If auto-detection fails, the Firestore document status should be set to `error` with a message: `"Could not parse file. Please ensure it is a standard comma-separated CSV with UTF-8 encoding."`
    * **Password-Protected Excel:** The system should detect this and return an error: `"Cannot process password-protected Excel files."`
* **AI Processing & API Failures:**
    * **LLM API Failure:** If a call to OpenAI/Google fails (e.g., API is down, invalid key), the job should retry 2-3 times with exponential backoff. If it still fails, set status to `error` with message: `"Could not connect to AI service. Please try again later."`
    * **Nonsensical AI Output:** If the LLM returns malformed JSON or irrelevant text, the backend should catch this, log the error, and return a user-friendly message: `"AI analysis failed to produce a valid result."`
* **Database/System:**
    * **DB Connection Error:** The API should return a `503 Service Unavailable` status if it cannot connect to Firestore.
    * **Orphaned Files:** A cleanup job should be considered (V2) to remove files from Storage whose corresponding Firestore records were never finalized or were deleted.

## 7. Dependencies

* **From Component 1 (Planning):** Needs the `ExperimentID` to correctly associate the uploaded data with a specific research plan.
* **To Component 3 (Analysis):** Must provide a finalized `Data Artifact` record containing a path to the clean data file and any associated notes. Component 3 will listen for documents with `status: 'ready_for_analysis'`.

## 8. Acceptance Criteria

* A user can upload a CSV, and it renders correctly in the UI.
* The AI successfully identifies and suggests fixes for at least 3 distinct issue types (e.g., inconsistent values, data type mismatch, outliers).
* A user can upload a 15-second audio clip and receive a structured transcription.
* A user can upload a clear screenshot of a table and get a downloadable CSV of its contents.
* A user can add, edit, and save qualitative notes alongside their data.
* The system correctly handles at least two backend-specific edge cases (e.g., LLM API failure, incorrect file delimiter).

## 9. Data Privacy & Security Considerations (CRITICAL)

* **Data in Transit:** All communication between the frontend and the backend API must use HTTPS.
* **Data at Rest:** All user files and data stored in Firebase (Storage and Firestore) must be encrypted at rest.
* **Firebase Security Rules:** Implement strict rules. A user should only be able to read/write their own `data_artifacts` documents. Storage rules must prevent direct public access to files; files should only be accessible via short-lived signed URLs generated by the backend when needed.
* **AI Data Processing:**
    * **Third-Party LLMs:** A privacy note must be in the UI.
    * **Data Minimization:** Send only the necessary data to the LLM.
    * **No Training:** API calls to the LLM provider must be configured to opt-out of using the data for model training.

## 10. API Contracts & Data Models

* **Firestore Model: `data_artifacts` collection**
    ```json
    {
      "artifactId": "uuid-1",
      "experimentId": "uuid-plan-A",
      "ownerId": "user-firebase-uid",
      "status": "pending_review | processing | ready_for_analysis | error",
      "originalFile": { "name": "raw_data.csv", "path": "gcs-path/..." },
      "cleanedFile": { "name": "clean_data.csv", "path": "gcs-path/..." },
      "suggestions": [
        {
          "suggestionId": "sugg-1",
          "type": "STANDARDIZE_CATEGORICAL",
          "column": "Gender",
          "details": { "valuesFound": ["M", "Male", "1"], "suggestion": "Male" }
        },
        {
          "suggestionId": "sugg-2",
          "type": "CONVERT_DATATYPE",
          "column": "Age",
          "details": { "from": "string", "to": "integer" }
        }
      ],
      "notes": "A free-form text field for qualitative observations...",
      "errorMessage": "Optional error message"
    }
    ```
* **Endpoint:** `POST /apply-suggestion`
    * **Request Body:**
        ```json
        {
          "artifactId": "uuid-1",
          "suggestionId": "sugg-1",
          "action": "accept" // or "reject"
        }
        ```
* **Endpoint:** `POST /update-notes`
    * **Request Body:**
        ```json
        {
          "artifactId": "uuid-1",
          "notes": "User's text notes go here."
        }
        ```
    * **Success Response (200 OK):**
        ```json
        {
          "status": "success",
          "message": "Notes updated successfully."
        }
        ```

## 11. Implementation Suggestions & Tooling

* **Python Backend:**
    * Use `pydantic` for robust data validation.
    * Use `python-multipart` for file uploads.
    * Use `pandas` for all tabular data manipulation.
    * Use `fastapi.BackgroundTasks` for simple background jobs or `Celery` with `Redis` for a more robust, scalable solution.
* **AI Logic & Prompting:**
    * **Chain of Thought:** For data cleaning, use a multi-step prompt. 1. "Analyze this column's values: `[v1, v2, ...]`. 2. Identify the data type (categorical, numerical, date). 3. If categorical, list all unique values. 4. Identify any inconsistencies or typos. 5. Suggest a single standard value. 6. Respond ONLY in this JSON format: `{...}`".
    * **Structured Output:** Use the LLM's function calling or JSON mode features to force it to return data in the exact format your backend expects. This avoids fragile string parsing.
* **Testing:** Use FastAPI's automatic Swagger UI (`/docs`) for endpoint testing. Write unit tests for data cleaning logic using `pytest` and mock data. 