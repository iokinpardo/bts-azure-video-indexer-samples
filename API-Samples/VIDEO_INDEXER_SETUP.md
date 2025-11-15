# Azure Video Indexer API Setup Guide

This guide walks through everything you need to do to run the Azure Video Indexer (VI) API samples in this repository and start indexing your own videos. Follow the steps in order—you will collect your API keys, configure the Python sample client, submit videos for indexing, and retrieve the resulting insights.

## 1. Prerequisites
- An active Azure subscription and Video Indexer account.
- Primary/secondary keys for Video Indexer (available in the [Video Indexer developer portal](https://api-portal.videoindexer.ai/profile)).
- Python 3.9+ with `pip`.
- The Azure CLI (`az`) signed into the same subscription that hosts your Video Indexer account if you want to authenticate via Azure AD instead of API keys.

## 2. Create or validate your Video Indexer account
1. Sign in to the [Azure portal](https://portal.azure.com/) and ensure the Video Indexer resource is provisioned (you can automate this with the `Deploy-Samples` folder if needed).
2. Open the [Video Indexer web experience](https://www.videoindexer.ai/) to finish setting up your account if it is the first time you sign in.
3. In the Video Indexer portal, note your **account name**, **account ID**, and the **region** (location) where the account resides.

## 3. Collect the API keys and IDs you will need
1. Browse to the [Video Indexer developer portal](https://api-portal.videoindexer.ai/profile).
2. Under **Subscriptions**, copy the **Primary key** and **Secondary key**; these are the API keys referred to by the samples.
3. Record the following values—you will need them in both `.env` and REST calls:
   - `ACCOUNT_ID`: The GUID of your Video Indexer account (visible under Account Settings in the Video Indexer portal or via the API `Get Accounts`).
   - `LOCATION`: The Azure region short name (e.g., `trial`, `eastus2`, `northeurope`).
   - `Ocp-Apim-Subscription-Key`: Either the primary or secondary key you copied from the developer portal.

## 4. Get an account access token with your API key
Most API calls require an access token scoped to the account or a specific video. You can generate the token directly with your API key.

```bash
curl -X GET "https://api.videoindexer.ai/Auth/{LOCATION}/Accounts/{ACCOUNT_ID}/AccessToken?allowEdit=true" \
     -H "Ocp-Apim-Subscription-Key: <PRIMARY_OR_SECONDARY_KEY>"
```

- Replace `{LOCATION}` with the value you collected earlier (for example, `trial`).
- Replace `{ACCOUNT_ID}` with your GUID.
- The response is a short-lived JWT access token. Use it in the `Authorization: Bearer {token}` header for subsequent requests (upload, list videos, widgets, etc.).
- Repeat the call whenever the token expires (typically one hour).

If you prefer the Azure AD flow demonstrated in the Python samples, skip the API key header and instead obtain an Azure Resource Manager token via `az account get-access-token --resource https://management.azure.com/` and exchange it using the same endpoint.

## 5. Prepare the repository and Python samples
1. Clone this repository and switch to the root folder.
2. Install dependencies:
   ```bash
   cd API-Samples/Python
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy the provided environment template:
   ```bash
   cp .env.example .env
   ```
4. Edit `.env` and fill in:
   - `AccountName`: The Video Indexer account name.
   - `AccountId`: The GUID collected earlier.
   - `AccountLocation`: The region (e.g., `trial`).
   - `ResourceGroup` / `SubscriptionId`: Required if you authenticate via Azure AD.
   - Any optional fields needed for your workflow (storage account, etc.).

## 6. Run the API sample notebook
1. Launch the notebook runner of your choice (VS Code, Jupyter, etc.).
2. Open `API-Samples/Python/video_indexer_api_samples.ipynb`.
3. Follow the notebook cells in order:
   - **Authenticate** using either the API key access token (paste it into the notebook when prompted) or Azure AD credentials.
   - **Upload videos** via URL (`upload_url_async`) or from local files (`file_upload_async`).
   - **Wait for indexing** using `wait_for_index_async` until the status is `Processed`.
   - **Retrieve insights** with `get_video_async` or by generating widget URLs.
4. Inspect the JSON output or open the generated widgets to confirm the insights you need (faces, OCR, keywords, sentiments, etc.).

## 7. (Optional) Automate uploads outside the notebook
If you prefer raw REST calls, the sequence is:
1. `GET /Auth/{location}/Accounts/{accountId}/AccessToken` to get a token (see Section 4).
2. `POST /{location}/Accounts/{accountId}/Videos` to upload or reference a video (include `Authorization: Bearer {token}` and your video metadata).
3. Poll `GET /{location}/Accounts/{accountId}/Videos/{videoId}/Index` until the `state` field equals `Processed`.
4. Fetch insights or widgets via `GET /{location}/Accounts/{accountId}/Videos/{videoId}` and `.../InsightsWidget` or `.../PlayerWidget`.

## 8. Testing the end-to-end flow
- Use a short sample video first (there is one under `media/`).
- Verify that the upload call returns a `videoId`.
- Confirm that the notebook prints the insights JSON and that the widget URLs load in your browser.

Once this checklist succeeds, your Azure Video Indexer service is ready to ingest production videos without deploying any additional infrastructure (such as Render.com). You can now automate uploads from your own apps using the same sequence of token generation, upload, polling, and insight retrieval.

## 9. Optional: Run the helper API on Render.com
Prefer not to run Python locally? Deploy the new FastAPI helper (`API-Samples/Python/render_service.py`) to
Render by following [`API-Samples/RENDER_DEPLOYMENT.md`](RENDER_DEPLOYMENT.md). The deployment uses the same
API key/token flow described above but exposes `/videos/url` and `/videos/{videoId}` endpoints that you can
call from any client once you configure your Video Indexer credentials as Render environment variables.
