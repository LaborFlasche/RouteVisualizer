from pyppeteer import launch
async def save_map_as_png(map_obj, file_path="map.png"):
    """Rendert eine Folium-Karte als PNG mit pyppeteer."""
    map_html = map_obj._repr_html_()

    browser = await launch(headless=True, args=["--no-sandbox"])
    page = await browser.newPage()
    await page.setViewport({"width": 800, "height": 600})
    await page.setContent(map_html)
    await page.screenshot({"path": file_path})
    await browser.close()
    return file_path