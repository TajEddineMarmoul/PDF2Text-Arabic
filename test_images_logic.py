import fitz

def _auto_detect_top_y_with_images(page: fitz.Page):
    doc = page.parent
    if not doc:
        return None
        
    rect = page.rect
    margin = rect.height * 0.15
    clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + margin)
    
    # 1. Get Top Images
    # Only consider images whose height is < 20% of the page height (so we don't crop full-page scans)
    def get_top_images(p: fitz.Page):
        images = []
        try:
            for info in p.get_image_info(hashes=True):
                ir = fitz.Rect(info["bbox"])
                # If image is in the top margin AND it's a small logo (not a full page scan)
                if ir.y0 < clip.y1 and ir.height < rect.height * 0.2:
                    images.append({
                        "bbox": info["bbox"],
                        "cy": (ir.y0 + ir.y1) / 2,
                        "digest": info.get("digest")
                    })
        except Exception:
            pass
        images.sort(key=lambda x: x["cy"])
        return images

    curr_images = get_top_images(page)
    
    if curr_images:
        first_img = curr_images[0]
        # Check if the same image repeats on prev or next page
        if page.number > 0:
            prev_images = get_top_images(doc[page.number - 1])
            if prev_images and prev_images[0].get("digest") == first_img.get("digest"):
                return first_img["bbox"][3] + 5
                
        if page.number < len(doc) - 1:
            next_images = get_top_images(doc[page.number + 1])
            if next_images and next_images[0].get("digest") == first_img.get("digest"):
                return first_block["bbox"][3] + 5 # Wait, first_img["bbox"][3] + 5
                
    return None
