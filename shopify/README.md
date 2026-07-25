# Shopify Audio Upload Widget

Custom theme section that adds a drag-and-drop file upload widget to your product
page. Customers upload their doppler recording before checkout; the file URL is
automatically attached to the Shopify order and picked up by the pipeline.

## How It Works

1. Customer selects or drops their recording (.wav / .mp3 / .mp4 / .mov / .m4a / .aac)
2. The widget uploads it to your API (`POST /upload`)
3. The API stores it in S3 and returns a 7-day presigned URL
4. The URL is injected as a Shopify line item property (`audio_file`) at cart-add time
5. The Shopify order webhook fires → `_extract_audio_url()` in `backend/app.py` reads it → pipeline runs

## Installation

### 1. Set CORS on your API

In your Railway / Render dashboard, add the environment variable:

```
SHOPIFY_STORE_URL=https://your-store.myshopify.com
```

(Use your custom domain instead if you have one.)

### 2. Upload files to your Shopify theme

In **Shopify Admin → Online Store → Themes → ⋯ → Edit code**:

**Sections:**
- Click **Add a new section**
- Name it `audio-upload`
- Paste the full contents of `sections/audio-upload.liquid`
- Save

**Assets:**
- Click **Add a new asset**
- Upload the file `assets/audio-upload.js`
- Save

### 3. Add the section to your product page

In **Shopify Admin → Online Store → Themes → Customize**:

1. Navigate to a **Product** page
2. In the left panel, click **Add section**
3. Choose **Audio Upload** from the list
4. In the section settings, set **API upload URL** to:
   `https://your-api.railway.app/upload`
5. Drag the section to sit just **above** the Add to Cart button
6. **Save**

### 4. Test it

1. Visit a product page on your store
2. The upload widget should appear above the Add to Cart button
3. Select a small audio file — the progress bar should fill, then show a ✓ checkmark
4. Click Add to Cart — the order should include a line item property `audio_file`
5. In Shopify Admin → Orders, open the order and confirm the property is visible

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Widget appears but upload fails | Check CORS — `SHOPIFY_STORE_URL` env var must match your store's exact origin |
| "API URL not configured" in console | Set the API upload URL in Theme Customizer → Audio Upload settings |
| Cart submits without uploading | Check that "Require upload before adding to cart" is enabled in section settings |
| `audio_file` property missing from order | Ensure the section is on a page that has a `form[action="/cart/add"]` element |
