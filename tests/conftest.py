"""Shared fixtures and HTML constants for webagentaudit tests."""

from typing import Optional

import pytest

from webagentaudit.detection.models import PageData


@pytest.fixture
def make_page_data():
    """Factory fixture that creates a PageData instance from HTML and optional params."""

    def _factory(
        html: str,
        url: str = "https://example.com",
        scripts: Optional[list[str]] = None,
        inline_scripts: Optional[list[str]] = None,
    ) -> PageData:
        return PageData(
            url=url,
            html=html,
            scripts=scripts or [],
            inline_scripts=inline_scripts or [],
        )

    return _factory


# ---------------------------------------------------------------------------
# Realistic HTML constants for test scenarios
# ---------------------------------------------------------------------------

SIMPLE_BLOG_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Personal Blog - Latest Posts</title>
    <link rel="stylesheet" href="/assets/css/main.css">
</head>
<body>
    <header class="site-header">
        <nav class="main-nav">
            <a href="/" class="logo">MyBlog</a>
            <ul class="nav-links">
                <li><a href="/about">About</a></li>
                <li><a href="/archive">Archive</a></li>
                <li><a href="/contact">Contact</a></li>
            </ul>
        </nav>
    </header>
    <main class="content-area">
        <article class="post">
            <h1>Understanding Modern Web Architecture</h1>
            <time datetime="2025-11-01">November 1, 2025</time>
            <p>In today's fast-paced development world, understanding web architecture
               is more important than ever. Let's explore the key components that make
               modern web applications tick.</p>
            <p>Server-side rendering, client-side hydration, and edge computing are
               transforming how we think about performance and user experience.</p>
        </article>
        <aside class="sidebar">
            <h3>Recent Posts</h3>
            <ul>
                <li><a href="/post/css-grid">CSS Grid Deep Dive</a></li>
                <li><a href="/post/typescript">TypeScript Best Practices</a></li>
            </ul>
        </aside>
    </main>
    <footer class="site-footer">
        <p>&copy; 2025 MyBlog. All rights reserved.</p>
    </footer>
    <script src="/assets/js/analytics.js"></script>
</body>
</html>
"""

CONTACT_FORM_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Us - Acme Corp</title>
    <link rel="stylesheet" href="/css/styles.css">
</head>
<body>
    <header>
        <div class="container">
            <a href="/" class="brand">Acme Corp</a>
            <nav>
                <a href="/products">Products</a>
                <a href="/pricing">Pricing</a>
                <a href="/contact" class="active">Contact</a>
            </nav>
        </div>
    </header>
    <main class="page-contact">
        <div class="container">
            <h1>Get in Touch</h1>
            <p>Have a question? Fill out the form below and we'll get back to you
               within 24 hours.</p>
            <form action="/api/contact" method="POST" class="contact-form">
                <div class="form-group">
                    <label for="name">Full Name</label>
                    <input type="text" id="name" name="name" placeholder="John Doe" required>
                </div>
                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input type="email" id="email" name="email" placeholder="john@example.com" required>
                </div>
                <div class="form-group">
                    <label for="subject">Subject</label>
                    <input type="text" id="subject" name="subject" placeholder="How can we help?">
                </div>
                <div class="form-group">
                    <label for="message">Your Message</label>
                    <textarea id="message" name="message" rows="5"
                              placeholder="Tell us about your project..."></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Send Message</button>
            </form>
        </div>
    </main>
    <footer>
        <p>&copy; 2025 Acme Corp</p>
    </footer>
</body>
</html>
"""

INTERCOM_CHAT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Help Center - SaaS Platform</title>
    <link rel="stylesheet" href="/css/app.css">
</head>
<body>
    <header class="top-bar">
        <div class="container">
            <a href="/" class="brand-logo">SaaSApp</a>
            <nav class="top-nav">
                <a href="/features">Features</a>
                <a href="/docs">Documentation</a>
                <a href="/support">Support</a>
            </nav>
        </div>
    </header>
    <main class="help-content">
        <div class="container">
            <h1>Help Center</h1>
            <div class="search-box">
                <input type="search" placeholder="Search help articles...">
            </div>
            <div class="help-categories">
                <div class="category-card">
                    <h3>Getting Started</h3>
                    <p>Learn the basics of our platform</p>
                </div>
                <div class="category-card">
                    <h3>Account & Billing</h3>
                    <p>Manage your subscription and payments</p>
                </div>
            </div>
        </div>
    </main>
    <div id="intercom-container" class="intercom-lightweight-app">
        <div class="intercom-launcher-frame">
            <div class="intercom-launcher" role="button" aria-label="Open chat">
                <svg viewBox="0 0 28 32"><path d="M28 32s-4.7-1.5-8-4..."></path></svg>
            </div>
        </div>
        <div class="intercom-messenger-frame" aria-label="chat assistant">
            <div class="intercom-messenger">
                <div class="intercom-conversation-list chat-messages">
                    <div class="intercom-message" data-testid="message-bubble">
                        <p>Hi there! How can we help you today?</p>
                    </div>
                </div>
                <div class="intercom-composer">
                    <textarea placeholder="Ask us anything..."
                              class="intercom-composer-textarea"
                              aria-label="Message composer"></textarea>
                    <button class="intercom-send-btn">Send</button>
                </div>
            </div>
        </div>
    </div>
    <script src="https://widget.intercom.io/widget/abc123def"></script>
    <script src="/js/app.bundle.js"></script>
</body>
</html>
"""

DRIFT_WIDGET_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pricing - Enterprise Solutions</title>
    <link rel="stylesheet" href="/css/marketing.css">
</head>
<body>
    <header class="navbar">
        <div class="container">
            <a href="/" class="logo">EnterpriseCo</a>
            <nav>
                <a href="/solutions">Solutions</a>
                <a href="/pricing" class="active">Pricing</a>
                <a href="/demo">Request Demo</a>
            </nav>
        </div>
    </header>
    <main>
        <section class="pricing-hero">
            <h1>Simple, Transparent Pricing</h1>
            <p>Choose the plan that's right for your team</p>
        </section>
        <section class="pricing-grid">
            <div class="pricing-card">
                <h2>Starter</h2>
                <p class="price">$29/mo</p>
                <ul>
                    <li>5 team members</li>
                    <li>10GB storage</li>
                </ul>
            </div>
            <div class="pricing-card featured">
                <h2>Professional</h2>
                <p class="price">$99/mo</p>
                <ul>
                    <li>25 team members</li>
                    <li>100GB storage</li>
                </ul>
            </div>
        </section>
    </main>
    <div class="drift-widget" id="drift-widget">
        <div class="drift-frame-controller">
            <iframe title="Drift Widget Chat" src="about:blank"></iframe>
        </div>
    </div>
    <script src="https://js.driftt.com/include/abc123/drift.min.js"></script>
    <script src="/js/pricing.js"></script>
</body>
</html>
"""

TIDIO_EMBED_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Online Store - Best Deals</title>
    <link rel="stylesheet" href="/css/shop.css">
</head>
<body>
    <header class="store-header">
        <a href="/" class="store-name">BestDeals</a>
        <div class="header-actions">
            <a href="/cart" class="cart-link">Cart (0)</a>
            <a href="/account">My Account</a>
        </div>
    </header>
    <main class="product-listing">
        <h1>Featured Products</h1>
        <div class="product-grid">
            <div class="product-card">
                <img src="/img/product1.jpg" alt="Wireless Headphones">
                <h3>Wireless Headphones</h3>
                <p class="price">$49.99</p>
                <button class="btn-add-cart">Add to Cart</button>
            </div>
            <div class="product-card">
                <img src="/img/product2.jpg" alt="Smart Watch">
                <h3>Smart Watch</h3>
                <p class="price">$129.99</p>
                <button class="btn-add-cart">Add to Cart</button>
            </div>
        </div>
    </main>
    <div id="tidio-chat" class="tidio-chat-container">
        <div class="tidio-chat-widget">
            <div class="tidio-chat-messages message-list-container">
                <div class="tidio-msg bot-msg">Welcome! Need help finding something?</div>
            </div>
            <div class="tidio-chat-input">
                <textarea placeholder="Type your message..." class="tidio-textarea"></textarea>
                <button class="tidio-send">Send</button>
            </div>
        </div>
    </div>
    <script src="https://code.tidio.co/xyz789abc.js"></script>
    <footer class="store-footer">
        <p>&copy; 2025 BestDeals</p>
    </footer>
</body>
</html>
"""

CHATBOT_WRAPPER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Support - TechCorp</title>
    <link rel="stylesheet" href="/css/support.css">
</head>
<body>
    <header class="main-header">
        <div class="container">
            <a href="/" class="logo">TechCorp</a>
            <nav>
                <a href="/products">Products</a>
                <a href="/support" class="active">Support</a>
                <a href="/community">Community</a>
            </nav>
        </div>
    </header>
    <main class="support-page">
        <div class="container">
            <h1>Customer Support</h1>
            <p>Need help? Our AI assistant is available 24/7 to answer your questions.</p>
        </div>
    </main>
    <div class="chatbot-wrapper" data-chatbot-id="techcorp-support">
        <div class="chatbot-header">
            <span class="chatbot-title">TechCorp Assistant</span>
            <button class="chatbot-close">&times;</button>
        </div>
        <div class="chatbot-conversation-log chat-log-area">
            <div class="chatbot-message bot">
                <p>Hello! I'm TechCorp's support assistant. How can I help you today?</p>
            </div>
        </div>
        <div class="chatbot-input-area">
            <textarea placeholder="Ask me anything about our products..."
                      class="chatbot-textarea"></textarea>
            <button class="chatbot-send-btn">Send</button>
        </div>
    </div>
    <script src="/js/chatbot-bundle.js"></script>
</body>
</html>
"""

DATA_TESTID_PROMPT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Assistant - DemoApp</title>
    <link rel="stylesheet" href="/css/app.css">
</head>
<body>
    <div id="app-root">
        <header class="app-header">
            <h1 class="app-title">DemoApp AI</h1>
            <div class="user-menu">
                <img src="/img/avatar.png" alt="User" class="avatar">
                <span>Jane Smith</span>
            </div>
        </header>
        <main class="chat-interface">
            <div class="conversation-panel" data-testid="message-list">
                <div class="msg-row assistant" data-testid="message-row">
                    <div class="msg-avatar">AI</div>
                    <div class="msg-content" data-testid="message-content">
                        <p>Welcome! I can help you with data analysis, writing, and more.</p>
                    </div>
                </div>
            </div>
            <div class="input-panel">
                <div data-testid="prompt-input" class="prompt-input-wrapper">
                    <textarea placeholder="Ask me anything..."
                              class="prompt-textarea"
                              rows="3"></textarea>
                    <button class="send-btn" data-testid="send-button">
                        <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
                    </button>
                </div>
            </div>
        </main>
    </div>
    <script src="/js/app.js"></script>
</body>
</html>
"""

MULTI_PROVIDER_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Digital Agency - MultiWidget Page</title>
    <link rel="stylesheet" href="/css/agency.css">
</head>
<body>
    <header>
        <nav class="navbar">
            <a href="/" class="brand">DigitalAgency</a>
            <div class="nav-items">
                <a href="/services">Services</a>
                <a href="/portfolio">Portfolio</a>
                <a href="/contact">Contact</a>
            </div>
        </nav>
    </header>
    <main>
        <section class="hero">
            <h1>We Build Digital Experiences</h1>
            <p>From web apps to mobile, we've got you covered.</p>
            <a href="/contact" class="cta-button">Get Started</a>
        </section>
    </main>
    <script src="https://widget.intercom.io/widget/agency123"></script>
    <script src="https://js.driftt.com/include/xyz456/drift.min.js"></script>
    <script src="/js/main.js"></script>
</body>
</html>
"""

ARIA_LABEL_CHAT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Support Portal - CloudService</title>
    <link rel="stylesheet" href="/css/portal.css">
</head>
<body>
    <header class="portal-header">
        <a href="/" class="portal-brand">CloudService</a>
        <nav class="portal-nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/docs">Docs</a>
            <a href="/status">Status</a>
        </nav>
    </header>
    <main class="portal-main">
        <div class="container">
            <h1>How can we help?</h1>
            <div class="search-wrapper">
                <input type="search" placeholder="Search documentation..."
                       class="doc-search">
            </div>
            <div class="topic-grid">
                <div class="topic-card">
                    <h3>Getting Started</h3>
                    <p>Quick start guides and tutorials</p>
                </div>
                <div class="topic-card">
                    <h3>API Reference</h3>
                    <p>Complete API documentation</p>
                </div>
            </div>
        </div>
    </main>
    <div aria-label="chat assistant" class="support-widget" role="complementary">
        <div class="widget-header">
            <span>Cloud Support</span>
            <button aria-label="Close chat" class="widget-close">&times;</button>
        </div>
        <div class="widget-body">
            <div class="widget-messages" role="log">
                <div class="widget-msg bot-msg">
                    <p>Hi! I'm CloudService's virtual assistant. Ask me anything.</p>
                </div>
            </div>
            <div class="widget-input">
                <textarea placeholder="Type your question..."
                          aria-label="chat message input"></textarea>
                <button class="widget-send">Send</button>
            </div>
        </div>
    </div>
    <script src="/js/support-widget.js"></script>
</body>
</html>
"""
