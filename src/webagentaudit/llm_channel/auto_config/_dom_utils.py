"""DOM utility functions for extracting element properties."""

from __future__ import annotations

from playwright.async_api import ElementHandle, Frame, Page

from .models import ElementCandidate


async def is_element_visible(el: ElementHandle) -> bool:
    """Check whether a Playwright element handle is visible on the page.

    An element is considered visible when it is attached to the DOM,
    not hidden via ``display: none`` / ``visibility: hidden`` / zero size,
    and is within the viewport (Playwright's built-in check).
    """
    try:
        return await el.is_visible()
    except Exception:
        return False


async def extract_element_props(
    el: ElementHandle, page: Page | Frame
) -> ElementCandidate:
    """Read properties of a DOM element and return an ``ElementCandidate``.

    The ``selector`` field is left empty — callers should fill it in
    via ``SelectorBuilder.build()`` after calling this function.
    """

    props: dict = await el.evaluate(
        """el => {
            const bb = el.getBoundingClientRect();
            const parentEl = el.parentElement;
            const parentClasses = [];
            let p = parentEl;
            for (let i = 0; i < 3 && p; i++) {
                if (p.className && typeof p.className === 'string') {
                    p.className.split(/\\s+/).filter(Boolean).forEach(c => parentClasses.push(c));
                }
                p = p.parentElement;
            }
            return {
                tagName: el.tagName.toLowerCase(),
                classes: el.className && typeof el.className === 'string'
                    ? el.className.split(/\\s+/).filter(Boolean)
                    : [],
                placeholder: el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                role: el.getAttribute('role') || '',
                type: el.getAttribute('type') || '',
                title: el.getAttribute('title') || '',
                isContenteditable: el.getAttribute('contenteditable') === 'true',
                dataTestid: el.getAttribute('data-testid') || '',
                hasSvgChild: !!el.querySelector('svg'),
                textContent: (el.textContent || '').trim().substring(0, 200),
                parentClasses: parentClasses,
                boundingBox: bb.width > 0 && bb.height > 0
                    ? { x: bb.x, y: bb.y, width: bb.width, height: bb.height }
                    : null,
            };
        }"""
    )

    return ElementCandidate(
        tag_name=props.get("tagName", ""),
        classes=props.get("classes", []),
        placeholder=props.get("placeholder", ""),
        aria_label=props.get("ariaLabel", ""),
        role=props.get("role", ""),
        element_type=props.get("type", ""),
        title=props.get("title", ""),
        is_contenteditable=props.get("isContenteditable", False),
        data_testid=props.get("dataTestid", ""),
        has_svg_child=props.get("hasSvgChild", False),
        text_content=props.get("textContent", ""),
        parent_classes=props.get("parentClasses", []),
        bounding_box=props.get("boundingBox"),
        # selector is left empty — caller fills it via SelectorBuilder
        selector="",
    )
