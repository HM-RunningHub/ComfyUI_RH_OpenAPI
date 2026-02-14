# RunningHub API Scraping Results

Successfully scraped 8 RunningHub model API endpoints from their detail pages.

## Summary

All endpoint information has been extracted and saved to `rh_api_scraping_results.json`.

### Models Scraped:

1. **全能视频S-图生视频** (Image-to-Video S)
   - Endpoint: `/rhart-video-s/image-to-video`
   - Parameters: imageUrl, duration, aspectRatio, prompt, storyboard, webhookUrl

2. **全能视频S-文生视频** (Text-to-Video S)
   - Endpoint: `/rhart-video-s/text-to-video`
   - Parameters: duration, prompt, aspectRatio, storyboard, webhookUrl

3. **全能图片V1-图生图** (Image V1 - Image Edit)
   - Endpoint: `/rhart-image-v1/edit`
   - Parameters: imageUrls, prompt, aspectRatio, webhookUrl

4. **全能图片PRO-图生图** (Image PRO - Image Edit)
   - Endpoint: `/rhart-image-n-pro/edit`
   - Parameters: imageUrls, prompt, resolution, aspectRatio, webhookUrl

5. **全能图片PRO-文生图** (Image PRO - Text-to-Image)
   - Endpoint: `/rhart-image-n-pro/text-to-image`
   - Parameters: prompt, resolution, aspectRatio, webhookUrl

6. **全能图片PRO-官方-图生图** (Image PRO Official - Image Edit)
   - Endpoint: `/rhart-image-n-pro-official/edit`
   - Parameters: imageUrls, prompt, resolution, aspectRatio, webhookUrl

7. **全能图片PRO-官方-文生图** (Image PRO Official - Text-to-Image)
   - Endpoint: `/rhart-image-n-pro-official/text-to-image`
   - Parameters: prompt, resolution, aspectRatio, webhookUrl

8. **全能图片G-1.5-文生图** (Image G-1.5 - Text-to-Image)
   - Endpoint: `/rhart-image-g-1.5/text-to-image`
   - Parameters: prompt, aspectRatio, webhookUrl

## Data Structure

Each model entry contains:
- `name`: Model display name in Chinese
- `endpoint`: API endpoint path
- `url`: Original detail page URL
- `params`: Array of parameter objects with:
  - `name`: Parameter name
  - `type`: Data type
  - `required`: Whether the parameter is required (true/false)
  - `description`: Parameter description
  - `enumValues`: Array of allowed values (if applicable) or null

## Notes

- The first two video models were fully verified with actual API documentation
- Image model parameters were inferred from the playground interface and WebFetch results
- All endpoints follow the RunningHub standard format: `/rhart-{model}/{operation}`
- Common parameters across models: `prompt`, `aspectRatio`, `webhookUrl`
- Video models support `storyboard` (Boolean) for scene generation
- PRO models support multiple resolutions (1k, 4k)
