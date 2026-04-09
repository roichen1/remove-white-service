@app.post("/remove-white")
async def remove_white(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    threshold: int = Form(245),
    color_tolerance: int = Form(18),
    edge_only: bool = Form(True),
    feather: float = Form(0.8),
    dehalo: bool = Form(True),
) -> Response:
    if file is None and url is None:
        raise HTTPException(status_code=400, detail="provide either 'file' or 'url'")
    if file is not None and url is not None:
        raise HTTPException(status_code=400, detail="provide only one of 'file' or 'url', not both")

    if not (0 <= threshold <= 255):
        raise HTTPException(status_code=400, detail="threshold must be between 0 and 255")
    if not (0 <= color_tolerance <= 255):
        raise HTTPException(status_code=400, detail="color_tolerance must be between 0 and 255")
    if not (0 <= feather <= 20):
        raise HTTPException(status_code=400, detail="feather must be between 0 and 20")

    if file is not None:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="empty file")
    else:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                response = await client.get(url)
            response.raise_for_status()
            image_bytes = response.content
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=400, detail=f"failed to fetch url: {exc.response.status_code}") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=400, detail=f"failed to fetch url: {exc}") from exc
        if not image_bytes:
            raise HTTPException(status_code=400, detail="empty response from url")

    try:
        result = remove_white_background(
            image_bytes=image_bytes,
            threshold=threshold,
            color_tolerance=color_tolerance,
            edge_only=edge_only,
            feather=feather,
            dehalo=dehalo,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"processing failed: {exc}") from exc

    return Response(content=result, media_type="image/png")
