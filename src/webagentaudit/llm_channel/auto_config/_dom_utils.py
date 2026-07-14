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


async def is_element_interactable(el: ElementHandle) -> bool:
    """Return whether an element is usable without triggering action waits."""
    if not await is_element_visible(el):
        return False
    try:
        if not await el.is_enabled():
            return False
        needs_editable = await el.evaluate(
            "el => ['INPUT', 'TEXTAREA'].includes(el.tagName) "
            "|| el.isContentEditable || el.getAttribute('role') === 'textbox'"
        )
        if needs_editable and not await el.is_editable():
            return False
        return await el.evaluate(
            """el => {
                const rect = el.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                // Below-the-fold controls are usable after Playwright scrolls
                // to them during the real interaction. Avoid doing that while
                // merely ranking candidates because scrolling is stateful and
                // can inherit a long action timeout.
                if (centerX < 0 || centerX > window.innerWidth
                    || centerY < 0 || centerY > window.innerHeight) return true;
                const top = document.elementFromPoint(
                    centerX,
                    centerY,
                );
                return !!top && (top === el || el.contains(top));
            }"""
        )
    except Exception:
        return False


async def click_enabled_submit_after_fill(
    page: Page | Frame, input_selector: str
) -> bool:
    """Click the closest enabled, semantically identifiable submit control.

    Some chat UIs render their send button disabled until text has been entered,
    so it cannot be safely selected during initial discovery.  This is a
    deliberately narrow fallback; callers should still use Enter when it finds
    no recognisable submit control.
    """
    try:
        return await page.evaluate(
            """(inputSelector) => {
                let input;
                try { input = document.querySelector(inputSelector); } catch (_) { return false; }
                if (!input) return false;

                const rect = input.getBoundingClientRect();
                const visible = (el) => {
                    const box = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    return box.width > 0 && box.height > 0
                        && style.visibility !== 'hidden' && style.display !== 'none';
                };
                const distance = (el) => {
                    const box = el.getBoundingClientRect();
                    return Math.hypot(
                        box.left + box.width / 2 - (rect.left + rect.width / 2),
                        box.top + box.height / 2 - (rect.top + rect.height / 2),
                    );
                };
                const candidates = [...document.querySelectorAll(
                    "button, input[type='submit'], [role='button']"
                )].filter(el => !el.disabled && visible(el)).map(el => {
                    const text = [
                        el.textContent, el.getAttribute('aria-label'),
                        el.getAttribute('title'), el.className,
                    ].filter(value => typeof value === 'string').join(' ').toLowerCase();
                    const semantic = /\\b(send|submit|ask|go)\\b/.test(text);
                    const submitType = el.getAttribute('type') === 'submit';
                    return { el, semantic, submitType, distance: distance(el) };
                }).filter(item => item.semantic || item.submitType);

                candidates.sort((a, b) =>
                    Number(b.semantic) - Number(a.semantic)
                    || Number(b.submitType) - Number(a.submitType)
                    || a.distance - b.distance
                );
                if (!candidates.length) return false;
                candidates[0].el.click();
                return true;
            }""",
            input_selector,
        )
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
            const labels = el.labels ? [...el.labels].map(label => label.textContent || '') : [];
            const wrappingLabel = el.closest('label');
            if (wrappingLabel) labels.push(wrappingLabel.textContent || '');
            const form = el.closest('form');
            return {
                tagName: el.tagName.toLowerCase(),
                id: el.id || '',
                classes: el.className && typeof el.className === 'string'
                    ? el.className.split(/\\s+/).filter(Boolean)
                    : [],
                placeholder: el.getAttribute('placeholder') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                role: el.getAttribute('role') || '',
                type: el.getAttribute('type') || '',
                title: el.getAttribute('title') || '',
                name: el.getAttribute('name') || '',
                autocomplete: el.getAttribute('autocomplete') || '',
                inputMode: el.getAttribute('inputmode') || '',
                labelText: labels.join(' ').trim().substring(0, 300),
                formContext: form
                    ? `${form.id} ${form.className || ''} ${form.getAttribute('role') || ''}`.substring(0, 300)
                    : '',
                isContenteditable: el.getAttribute('contenteditable') === 'true',
                dataTestid: el.getAttribute('data-testid') || '',
                hasSvgChild: !!el.querySelector('svg'),
                textContent: (el.textContent || '').trim().substring(0, 200),
                parentClasses: parentClasses,
                boundingBox: bb.width > 0 && bb.height > 0
                    ? {
                        x: bb.x, y: bb.y, width: bb.width, height: bb.height,
                        viewportWidth: window.innerWidth, viewportHeight: window.innerHeight,
                    }
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
        element_id=props.get("id", ""),
        name=props.get("name", ""),
        autocomplete=props.get("autocomplete", ""),
        input_mode=props.get("inputMode", ""),
        label_text=props.get("labelText", ""),
        form_context=props.get("formContext", ""),
        is_contenteditable=props.get("isContenteditable", False),
        data_testid=props.get("dataTestid", ""),
        has_svg_child=props.get("hasSvgChild", False),
        text_content=props.get("textContent", ""),
        parent_classes=props.get("parentClasses", []),
        bounding_box=props.get("boundingBox"),
        # selector is left empty — caller fills it via SelectorBuilder
        selector="",
    )
