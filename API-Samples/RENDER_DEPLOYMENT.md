# Deploy the Azure Video Indexer helper API to Render.com

The Python samples now include a lightweight FastAPI service (`API-Samples/Python/render_service.py`)
that wraps the Azure Video Indexer API using your existing primary/secondary keys. Deploying this
service to [Render.com](https://render.com) lets you upload videos and retrieve insights from any
browser or REST client without configuring a local Python environment.

## 1. Prerequisites
- A Render account connected to the GitHub fork/clone of this repository.
- Primary or secondary API key from the [Azure Video Indexer developer portal](https://api-portal.videoindexer.ai/profile).
- Your Video Indexer account ID and location (region short name).

## 2. Required environment variables
Configure the following secrets in Render (Dashboard ➜ *Environment ➜ Secret Files & Env Vars*):

| Variable | Purpose |
| --- | --- |
| `VI_ACCOUNT_ID` | GUID of your Video Indexer account. |
| `VI_LOCATION` | Region short name (e.g., `trial`, `eastus2`, `northeurope`). |
| `VI_SUBSCRIPTION_KEY` | Primary or secondary API key copied from the developer portal. |
| `VI_DEFAULT_LANGUAGE` *(optional)* | Defaults to `English` for insight translation. |
| `VI_API_ENDPOINT` *(optional)* | Override only if you use a sovereign cloud endpoint. |
| `VI_POLL_INTERVAL_SECONDS` *(optional)* | Poll cadence while waiting for indexing (default `10`). |
| `VI_WAIT_TIMEOUT_SECONDS` *(optional)* | Maximum seconds to wait for indexing (default `900`). |
| `VI_TOKEN_TTL_SECONDS` *(optional)* | Cache duration for access tokens (default `3300`). |

Render also injects a `PORT` variable; the FastAPI service binds to this automatically when you use
the provided start command.

## 3. Use the provided `render.yaml`
This repository ships with a ready-to-use [Render blueprint](../render.yaml). After connecting your
GitHub account to Render:

1. Click **New ➜ Blueprint** in the Render dashboard.
2. Select your fork and the `docs/render-deployment-20240725` (or later) branch that contains
   `render.yaml`.
3. Review the service definition:
   - Runtime: Python 3.x
   - Build command: `pip install -r API-Samples/Python/requirements.txt`
   - Start command: `bash -c "cd API-Samples/Python && uvicorn render_service:app --host 0.0.0.0 --port $PORT"`
4. Provide the environment variables listed above when prompted.
5. Click **Apply** to let Render create the web service.

Whenever you push updates to this repository, Render can auto-deploy (enabled by default in the
blueprint). You can also trigger deployments manually from the dashboard.

## 4. Manual setup (if you prefer not to use blueprints)
1. Click **New ➜ Web Service**.
2. Choose your repository and branch, then select the Python environment.
3. Set the build and start commands exactly as described in Section 3.
4. Define the environment variables in the *Environment* tab.
5. Deploy.

## 5. Smoke-test the deployment
Once Render finishes provisioning, locate the generated service URL (for example,
`https://video-indexer-helper.onrender.com`). Use a REST client or curl to verify:

```bash
# Health probe
curl https://video-indexer-helper.onrender.com/healthz

# Upload a video by URL and wait for indexing
curl -X POST https://video-indexer-helper.onrender.com/videos/url \
     -H "Content-Type: application/json" \
     -d '{
           "name": "sample",
           "video_url": "https://contoso.com/video.mp4",
           "wait_for_index": true,
           "include_index_payload": true
         }'
```

The response body includes the `videoId`, the final state (`Processed`/`Failed`), and—if requested—the
full insights payload.

## 6. How this service fits with the rest of the samples
- `render_service.py` uses the same API flow demonstrated in
  [`VIDEO_INDEXER_SETUP.md`](VIDEO_INDEXER_SETUP.md) but hides the token exchange behind a web API.
- You can keep using the notebook locally; deployments to Render are optional and coexist with the
  local samples.
- Because the service only stores tokens in memory, no Video Indexer data is persisted on Render.

## 7. Common troubleshooting tips
| Symptom | Resolution |
| --- | --- |
| `401 Unauthorized` from Video Indexer | Confirm `VI_SUBSCRIPTION_KEY`, account ID, and location match the developer portal. |
| Deployment stuck on *Starting* | Ensure the start command references `$PORT` and `uvicorn` is listed in `requirements.txt`. |
| Upload succeeds but indexing never finishes | Increase `VI_WAIT_TIMEOUT_SECONDS` or disable `wait_for_index` in the request to poll manually. |

After smoke-testing, you can embed the Render URL in your tools or create a lightweight front-end
that calls the `/videos/url` and `/videos/{videoId}` endpoints.
