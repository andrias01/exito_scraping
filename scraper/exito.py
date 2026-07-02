"""
Scraper de productos de Éxito Colombia usando Playwright.
Implementa reintentos, rotación de User-Agent y manejo robusto de errores.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from config.settings import get_settings

logger = logging.getLogger(__name__)

# ─── User-Agents rotativos ────────────────────────────────────────────────────
USER_AGENTS: list[str] = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
]


# ─── Dataclass resultado ──────────────────────────────────────────────────────
@dataclass
class ProductoScraped:
    """Resultado del scraping de un producto."""

    url: str
    nombre: Optional[str] = None
    imagen_url: Optional[str] = None
    precio_normal: Optional[float] = None
    precio_tarjeta: Optional[float] = None
    descuento: Optional[float] = None
    disponible: bool = True
    fecha: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    @property
    def exitoso(self) -> bool:
        """True si el scraping fue exitoso."""
        return self.error is None and self.nombre is not None

    def to_dict(self) -> dict:
        """Serializa el resultado a diccionario."""
        return {
            "url": self.url,
            "nombre": self.nombre,
            "imagen_url": self.imagen_url,
            "precio_normal": self.precio_normal,
            "precio_tarjeta": self.precio_tarjeta,
            "descuento": self.descuento,
            "disponible": self.disponible,
            "fecha": self.fecha.isoformat(),
            "error": self.error,
            "exitoso": self.exitoso,
        }


# ─── Clase principal ──────────────────────────────────────────────────────────
class ExitoScraper:
    """
    Scraper para productos de Éxito Colombia.

    Reutiliza el navegador entre consultas para eficiencia.
    Implementa reintentos automáticos y detección de bloqueos.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._initialized = False

    async def __aenter__(self) -> "ExitoScraper":
        await self._start()
        return self

    async def __aexit__(self, *args) -> None:  # type: ignore[no-untyped-def]
        await self._stop()

    async def _start(self) -> None:
        """Inicia el navegador Playwright."""
        if self._initialized:
            return
        logger.info("Iniciando navegador Playwright (headless=%s)", self._settings.scraper_headless)
        self._playwright = await async_playwright().start()

        # Buscar Chromium del sistema (instalado por Nix en Railway) para evitar
        # el error "Executable doesn't exist" cuando Playwright no tiene su propio binario.
        system_chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        launch_kwargs: dict = {
            "headless": self._settings.scraper_headless,
            "slow_mo": self._settings.scraper_slow_mo,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        }
        if system_chromium:
            logger.info("Usando Chromium del sistema: %s", system_chromium)
            launch_kwargs["executable_path"] = system_chromium

        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        self._initialized = True
        logger.info("Navegador iniciado correctamente.")

    async def _stop(self) -> None:
        """Cierra el navegador y libera recursos."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False
        logger.info("Navegador cerrado.")

    async def _create_context(self) -> BrowserContext:
        """Crea un contexto del navegador con User-Agent aleatorio."""
        assert self._browser is not None, "El navegador no está inicializado."
        user_agent = random.choice(USER_AGENTS)
        context = await self._browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="es-CO",
            timezone_id="America/Bogota",
            extra_http_headers={
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,*/*;q=0.8"
                ),
            },
        )
        # Ocultar automatización
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return context

    @staticmethod
    def _parse_price(raw: str) -> Optional[float]:
        """Convierte un string de precio colombiano a float."""
        if not raw:
            return None
        clean = re.sub(r"[^\d]", "", raw)
        if not clean:
            return None
        try:
            return float(clean)
        except ValueError:
            return None

    async def _detect_block(self, page: Page) -> bool:
        """Detecta si la página está bloqueando el scraper."""
        title = (await page.title()).lower()
        url = page.url.lower()
        block_indicators = [
            "access denied",
            "captcha",
            "robot",
            "blocked",
            "403",
            "429",
            "forbidden",
        ]
        return any(indicator in title or indicator in url for indicator in block_indicators)

    async def _extract_product_data(self, page: Page, url: str) -> ProductoScraped:
        """Extrae los datos del producto desde la página cargada."""
        result = ProductoScraped(url=url)

        # Detectar bloqueo
        if await self._detect_block(page):
            result.error = "Página bloqueada por el servidor"
            logger.warning("Bloqueo detectado en: %s", url)
            return result

        # ── Nombre del producto ──────────────────────────────────────────────
        nombre = None
        nombre_selectors = [
            "h1.product-title",
            "h1[class*='product']",
            "h1[class*='title']",
            "[data-testid='product-name']",
            "[class*='ProductName']",
            "[class*='productName']",
            ".vtex-store-components-3-x-productNameContainer",
            "h1",
        ]
        for sel in nombre_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = (await el.inner_text()).strip()
                    if text and len(text) > 3:
                        nombre = text
                        break
            except Exception:
                continue

        result.nombre = nombre

        # ── Precio normal ────────────────────────────────────────────────────
        precio_normal = None
        precio_normal_selectors = [
            "[class*='listPrice'] span",
            "[class*='ListPrice']",
            "[class*='list-price']",
            ".vtex-product-price-1-x-listPrice",
            "[data-testid='list-price']",
            ".price-old",
            "[class*='originalPrice']",
            ".product-price-original",
        ]
        for sel in precio_normal_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = (await el.inner_text()).strip()
                    parsed = self._parse_price(text)
                    if parsed and parsed > 0:
                        precio_normal = parsed
                        break
            except Exception:
                continue

        # ── Precio tarjeta ───────────────────────────────────────────────────
        precio_tarjeta = None
        precio_tarjeta_selectors = [
            "[class*='sellingPrice'] span",
            "[class*='SellingPrice']",
            "[class*='selling-price']",
            ".vtex-product-price-1-x-sellingPrice",
            "[data-testid='selling-price']",
            ".price-current",
            "[class*='bestPrice']",
            ".product-price-current",
        ]
        for sel in precio_tarjeta_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    text = (await el.inner_text()).strip()
                    parsed = self._parse_price(text)
                    if parsed and parsed > 0:
                        precio_tarjeta = parsed
                        break
            except Exception:
                continue

        # Si solo hay un precio, usar como precio normal
        if precio_normal is None and precio_tarjeta is not None:
            # Buscar el precio principal (puede ser el único)
            main_price_selectors = [
                ".vtex-product-price-1-x-currencyContainer",
                "[class*='currencyContainer']",
                "[class*='price']",
                ".product-price",
            ]
            for sel in main_price_selectors:
                try:
                    elements = page.locator(sel)
                    count = await elements.count()
                    prices = []
                    for i in range(min(count, 5)):
                        text = (await elements.nth(i).inner_text()).strip()
                        parsed = self._parse_price(text)
                        if parsed and parsed > 100:
                            prices.append(parsed)
                    if len(prices) >= 2:
                        prices.sort(reverse=True)
                        precio_normal = prices[0]
                        precio_tarjeta = prices[1]
                        break
                    elif len(prices) == 1 and precio_normal is None:
                        precio_normal = prices[0]
                        break
                except Exception:
                    continue

        result.precio_normal = precio_normal
        result.precio_tarjeta = precio_tarjeta

        # ── Descuento ────────────────────────────────────────────────────────
        if precio_normal and precio_tarjeta and precio_tarjeta < precio_normal:
            result.descuento = round(
                ((precio_normal - precio_tarjeta) / precio_normal) * 100, 2
            )

        # ── Disponibilidad ───────────────────────────────────────────────────
        disponible = True
        unavailable_selectors = [
            "[class*='unavailable']",
            "[class*='outOfStock']",
            "[class*='out-of-stock']",
            "[data-testid='unavailable']",
        ]
        for sel in unavailable_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    disponible = False
                    break
            except Exception:
                continue

        # Verificar texto de no disponibilidad
        try:
            body_text = await page.locator("body").inner_text()
            unavailable_texts = [
                "agotado",
                "no disponible",
                "sin stock",
                "out of stock",
            ]
            if any(t in body_text.lower() for t in unavailable_texts):
                disponible = False
        except Exception:
            pass

        result.disponible = disponible

        # ── Imagen ───────────────────────────────────────────────────────────
        imagen_url = None
        image_selectors = [
            "[class*='productImage'] img",
            "[class*='ProductImage'] img",
            ".product-image img",
            "[data-testid='product-image'] img",
            "img[class*='product']",
            ".gallery-image img",
        ]
        for sel in image_selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    src = await el.get_attribute("src")
                    if src and src.startswith("http"):
                        imagen_url = src
                        break
            except Exception:
                continue

        result.imagen_url = imagen_url

        logger.info(
            "Producto extraído: %s | Normal: %s | Tarjeta: %s | Disponible: %s",
            result.nombre,
            result.precio_normal,
            result.precio_tarjeta,
            result.disponible,
        )
        return result

    async def scrape_url(self, url: str) -> ProductoScraped:
        """
        Realiza el scraping de un producto dado su URL.
        Implementa reintentos automáticos con backoff exponencial.
        """
        if not self._initialized:
            await self._start()

        settings = self._settings
        last_error: Optional[str] = None

        for attempt in range(1, settings.scraper_retries + 1):
            context: Optional[BrowserContext] = None
            page: Optional[Page] = None
            try:
                logger.info("Intento %d/%d para: %s", attempt, settings.scraper_retries, url)
                context = await self._create_context()
                page = await context.new_page()

                # Bloquear recursos innecesarios para mayor velocidad
                await page.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,ico,woff,woff2,ttf,eot}",
                    lambda route: route.abort()
                    if "product" not in route.request.url
                    else route.continue_(),
                )

                await page.goto(
                    url,
                    timeout=settings.scraper_timeout,
                    wait_until="domcontentloaded",
                )

                # Esperar contenido dinámico
                await page.wait_for_load_state("networkidle", timeout=15_000)

                # Esperar posible renderizado de precio
                try:
                    await page.wait_for_selector(
                        "[class*='price'], [class*='Price'], .product-price",
                        timeout=10_000,
                    )
                except PlaywrightTimeoutError:
                    logger.warning("Selector de precio no encontrado, continuando...")

                # Scroll para activar lazy loading
                await page.evaluate("window.scrollTo(0, 300)")
                await asyncio.sleep(1)

                result = await self._extract_product_data(page, url)

                if result.exitoso:
                    return result

                last_error = result.error or "Extracción fallida"

            except PlaywrightTimeoutError as exc:
                last_error = f"Timeout: {exc}"
                logger.warning("Timeout en intento %d: %s", attempt, exc)
            except Exception as exc:
                last_error = str(exc)
                logger.error("Error en intento %d: %s", attempt, exc, exc_info=True)
            finally:
                if page:
                    await page.close()
                if context:
                    await context.close()

            if attempt < settings.scraper_retries:
                delay = settings.scraper_retry_delay * (2 ** (attempt - 1))
                logger.info("Esperando %ds antes del reintento...", delay)
                await asyncio.sleep(delay)

        return ProductoScraped(url=url, error=last_error or "Error desconocido")

    async def scrape_multiple(self, urls: list[str]) -> list[ProductoScraped]:
        """Realiza el scraping de múltiples URLs secuencialmente."""
        results: list[ProductoScraped] = []
        for url in urls:
            result = await self.scrape_url(url)
            results.append(result)
            # Pausa entre peticiones para evitar rate limiting
            await asyncio.sleep(random.uniform(2.0, 4.0))
        return results
