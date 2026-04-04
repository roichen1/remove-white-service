# Remove White Background API

A tiny Railway-ready API for e-commerce graphics where the background is always white.

## What it does
- Removes **near-white background**
- By default removes only white that is **connected to the image edges**
- Preserves white details **inside** the artwork much better than "make all white transparent"
- Returns PNG with transparency

## Deploy on Railway
1. Create a new GitHub repo
2. Upload these 4 files:
   - `app.py`
   - `requirements.txt`
   - `Dockerfile`
   - `README.md`
3. In Railway choose **GitHub Repository**
4. Select the repo
5. Deploy

No extra variables are required.

## Health check
`GET /health`

## Main endpoint
`POST /remove-white`

### Multipart form-data fields
- `file` (required): image file
- `threshold` (optional, default `245`): how bright a pixel must be to count as background
- `color_tolerance` (optional, default `18`): how neutral/grayish the pixel must be
- `edge_only` (optional, default `true`): remove only background connected to the outer edges
- `feather` (optional, default `0.8`): softens the edge slightly to avoid jagged borders
- `dehalo` (optional, default `true`): removes white fringe around the subject

## Recommended defaults for cute e-commerce graphics
- `threshold=245`
- `color_tolerance=18`
- `edge_only=true`
- `feather=0.8`
- `dehalo=true`

If too much white remains:
- increase `color_tolerance` to `22-28`
- or lower `threshold` to `238-242`

If parts of the subject get eaten:
- lower `color_tolerance` to `10-15`
- or raise `threshold` to `248-252`

## Example curl
```bash
curl -X POST "https://YOUR-APP.up.railway.app/remove-white" \
  -F "file=@rocket.png" \
  -F "threshold=245" \
  -F "color_tolerance=18" \
  -F "edge_only=true" \
  -F "feather=0.8" \
  -F "dehalo=true" \
  --output result.png
```

## n8n setup
Use an **HTTP Request** node:
- Method: `POST`
- URL: `https://YOUR-APP.up.railway.app/remove-white`
- Send Body: `Form-Data`
- Add field `file` as **n8n Binary File**
- Add optional text fields for the parameters above
- Response format: `File`
- Put output binary property name as something like `data`

Then continue the workflow with the returned PNG.
