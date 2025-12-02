// --------------------
// Dark Mode Function
// --------------------
function visionDarkMode() {
    const body = document.body;
    const children = body.querySelectorAll("*"); // all elements

    const textColorDark = "#FFFFFF"; // white for dark mode
    const textColorLight = "#111111"; // black for light mode
    const darkBackground = "rgb(34,34,34)";
    const lightBackground = "white";

    function getBrightness(rgb) {
        const values = rgb.match(/\d+/g).map(Number);
        return (values[0] * 0.299 + values[1] * 0.587 + values[2] * 0.114);
    }

    children.forEach(el => {
        const style = getComputedStyle(el);
        const bg = style.backgroundColor;

        // Skip fully transparent backgrounds
        if (bg === "rgba(0, 0, 0, 0)" || bg === "transparent") return;

        const brightness = getBrightness(bg);

        // Set text color based on background brightness
        el.style.color = brightness < 128 ? textColorDark : textColorLight;

        // Optional: darken backgrounds that are too light in dark mode
        if (brightness > 200) {
            el.style.backgroundColor = "#555"; // subtle dark overlay
        }

        // Special handling for buttons
        if (el.tagName === "BUTTON") {
            el.style.backgroundColor = brightness < 128 ? "#fff" : el.style.backgroundColor;
            el.style.color = brightness < 128 ? "#000" : el.style.color;
        }
    });

    // Apply body dark mode
    body.style.backgroundColor = darkBackground;
    body.style.color = textColorDark;

    // Notify user with toast
    visionToast("Dark mode enabled!");
}

// --------------------
// Toast Notification Function
// --------------------
function visionToast(message, duration = 3000) {
    const toast = document.createElement("div");
    toast.className = "spark-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    toast.offsetWidth;
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-20px)";
        toast.addEventListener("transitionend", () => toast.remove());
    }, duration);
}

// --------------------
// Toast CSS Injection
// --------------------
(function injectToastCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%) translateY(20px);
            background-color: rgba(0,0,0,0.8);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            opacity: 0;
            pointer-events: none;
            transition: all 0.4s ease;
            z-index: 9999;
        }

        /* Reveal animation */
        .reveal {
            opacity: 0;
            transform: translateY(20px);
            transition: opacity 0.6s ease-out, transform 0.6s ease-out;
        }
        .reveal-active {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// On-Scroll Reveal Function
// --------------------
function visionScrollReveal() {
    const revealElements = document.querySelectorAll(".reveal");

    function reveal() {
        const windowHeight = window.innerHeight;
        revealElements.forEach(el => {
            const elementTop = el.getBoundingClientRect().top;
            const revealPoint = 150; // distance from bottom
            if (elementTop < windowHeight - revealPoint) {
                el.classList.add("reveal-active");
            } else {
                el.classList.remove("reveal-active");
            }
        });
    }

    window.addEventListener("scroll", reveal);
    // Trigger reveal on load
    reveal();
}
// --------------------
// Modal Function
// --------------------
function sparkModal(title, bodyText) {
    // Create modal background
    const modalBg = document.createElement("div");
    modalBg.className = "spark-modal-bg";

    // Create modal container
    const modal = document.createElement("div");
    modal.className = "spark-modal";

    // Create modal content
    const modalTitle = document.createElement("h2");
    modalTitle.textContent = title;

    const modalBody = document.createElement("p");
    modalBody.textContent = bodyText;

    // Create close button
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "×";
    closeBtn.className = "spark-modal-close";
    closeBtn.onclick = () => modalBg.remove();

    // Assemble modal
    modal.appendChild(closeBtn);
    modal.appendChild(modalTitle);
    modal.appendChild(modalBody);
    modalBg.appendChild(modal);
    document.body.appendChild(modalBg);

    // Optional: fade in
    setTimeout(() => {
        modalBg.style.opacity = "1";
    }, 10);
}

// --------------------
// Modal CSS Injection
// --------------------
(function injectModalCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-modal-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
            z-index: 10000;
        }
        .spark-modal {
            background-color: #fff;
            color: #000;
            padding: 20px 30px;
            border-radius: 10px;
            max-width: 500px;
            width: 90%;
            position: relative;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            font-family: Arial, sans-serif;
        }
        .spark-modal h2 {
            margin-top: 0;
            font-size: 20px;
        }
        .spark-modal p {
            margin: 10px 0 0;
        }
        .spark-modal-close {
            position: absolute;
            top: 10px;
            right: 15px;
            background: none;
            border: none;
            font-size: 22px;
            cursor: pointer;
        }

        /* Dark mode support */
        body.dark-mode .spark-modal {
            background-color: #222;
            color: #fff;
        }
    `;
    document.head.appendChild(style);
})();
// --------------------
// Live Character Counter
// --------------------
function sparkCharCount(inputSelector, counterSelector) {
    const input = document.querySelector(inputSelector);
    const counter = document.querySelector(counterSelector);

    if (!input || !counter) {
        console.warn("sparkCharCount: Input or counter element not found.");
        return;
    }

    // Initialize counter
    counter.textContent = input.value.length;

    // Update counter on input
    input.addEventListener("input", () => {
        counter.textContent = input.value.length;
    });
}

// --------------------
// Optional CSS for counter
// --------------------
(function injectCharCountCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-char-counter {
            font-size: 12px;
            color: #555;
            margin-top: 4px;
            display: inline-block;
        }

        /* Dark mode support */
        body.dark-mode .spark-char-counter {
            color: #ccc;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Countdown Timer
// --------------------
function sparkCountdown(targetDate, displaySelector) {
    const display = document.querySelector(displaySelector);
    if (!display) {
        console.warn("sparkCountdown: Display element not found.");
        return;
    }

    const endDate = new Date(targetDate).getTime();
    if (isNaN(endDate)) {
        console.warn("sparkCountdown: Invalid target date.");
        return;
    }

    function updateTimer() {
        const now = new Date().getTime();
        const distance = endDate - now;

        if (distance <= 0) {
            display.textContent = "Time's up!";
            clearInterval(interval);
            return;
        }

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        display.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    updateTimer(); // initial call
    const interval = setInterval(updateTimer, 1000);
}

// --------------------
// Optional Countdown CSS
// --------------------
(function injectCountdownCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-countdown {
            font-family: Arial, sans-serif;
            font-size: 16px;
            color: #333;
        }

        body.dark-mode .spark-countdown {
            color: #fff;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Smooth Scroll Navigator
// --------------------
function sparkSmoothScroll(targetSelector, offset = 0, duration = 800) {
    const target = document.querySelector(targetSelector);
    if (!target) {
        console.warn("sparkSmoothScroll: Target element not found.");
        return;
    }

    const startPosition = window.scrollY || window.pageYOffset;
    const targetPosition = target.getBoundingClientRect().top + startPosition - offset;
    const distance = targetPosition - startPosition;
    let startTime = null;

    function easeInOutQuad(t, b, c, d) {
        t /= d / 2;
        if (t < 1) return c / 2 * t * t + b;
        t--;
        return -c / 2 * (t * (t - 2) - 1) + b;
    }

    function animation(currentTime) {
        if (startTime === null) startTime = currentTime;
        const timeElapsed = currentTime - startTime;
        const run = easeInOutQuad(timeElapsed, startPosition, distance, duration);
        window.scrollTo(0, run);
        if (timeElapsed < duration) requestAnimationFrame(animation);
    }

    requestAnimationFrame(animation);
}
// --------------------
// Tab Component Generator
// --------------------
function sparkTabs(buttonSelector, contentSelector, activeClass = "active") {
    const buttons = document.querySelectorAll(buttonSelector);
    const contents = document.querySelectorAll(contentSelector);

    if (!buttons.length || !contents.length) {
        console.warn("sparkTabs: No buttons or content elements found.");
        return;
    }

    buttons.forEach((btn, index) => {
        btn.addEventListener("click", () => {
            // Remove active class from all buttons and content
            buttons.forEach(b => b.classList.remove(activeClass));
            contents.forEach(c => c.classList.remove(activeClass));

            // Add active class to clicked button and corresponding content
            btn.classList.add(activeClass);
            if (contents[index]) contents[index].classList.add(activeClass);
        });
    });
}

// --------------------
// Optional Tab CSS
// --------------------
(function injectTabCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .tab-buttons {
            display: flex;
            gap: 8px;
            cursor: pointer;
        }
        .tab-buttons .active {
            font-weight: bold;
            border-bottom: 2px solid #007BFF;
        }
        .tab-content {
            display: none;
            margin-top: 10px;
        }
        .tab-content.active {
            display: block;
        }

        /* Dark mode support */
        body.dark-mode .tab-buttons .active {
            border-color: #00ffff;
        }
        body.dark-mode .tab-content {
            color: #fff;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Accordion Component
// --------------------
function sparkAccordion(headerSelector, activeClass = "spark-acc-active") {
    const headers = document.querySelectorAll(headerSelector);

    if (!headers.length) {
        console.warn("sparkAccordion: No headers found.");
        return;
    }

    headers.forEach(header => {
        header.addEventListener("click", () => {
            // Toggle active class
            header.classList.toggle(activeClass);

            // Toggle panel display
            const panel = header.nextElementSibling;
            if (panel) {
                if (panel.style.maxHeight) {
                    panel.style.maxHeight = null;
                } else {
                    panel.style.maxHeight = panel.scrollHeight + "px";
                }
            }
        });
    });
}

// --------------------
// Accordion CSS Injection
// --------------------
(function injectAccordionCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-accordion {
            cursor: pointer;
            padding: 12px 20px;
            border: 1px solid #ccc;
            margin-bottom: 5px;
            border-radius: 5px;
            background-color: #f7f7f7;
            transition: background-color 0.3s;
        }
        .spark-accordion:hover {
            background-color: #e2e2e2;
        }
        .spark-acc-active {
            background-color: #ddd;
        }
        .spark-accordion + .spark-accordion-panel {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
            padding: 0 20px;
            background-color: #fafafa;
        }

        /* Dark mode support */
        body.dark-mode .spark-accordion {
            background-color: #333;
            color: #fff;
            border-color: #555;
        }
        body.dark-mode .spark-accordion:hover {
            background-color: #444;
        }
        body.dark-mode .spark-accordion + .spark-accordion-panel {
            background-color: #222;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Auto Image Slider / Carousel
// --------------------
function sparkSlider(containerSelector, intervalTime = 3000) {
    const container = document.querySelector(containerSelector);
    if (!container) {
        console.warn("sparkSlider: Container element not found.");
        return;
    }

    const slides = container.children;
    if (!slides.length) return;

    let currentIndex = 0;

    // Hide all slides initially
    Array.from(slides).forEach((slide, i) => {
        slide.style.display = i === 0 ? "block" : "none";
        slide.style.transition = "opacity 0.5s ease-in-out";
        slide.style.width = "100%";
    });

    // Slider function
    function nextSlide() {
        slides[currentIndex].style.display = "none";
        currentIndex = (currentIndex + 1) % slides.length;
        slides[currentIndex].style.display = "block";
    }

    const sliderInterval = setInterval(nextSlide, intervalTime);

    // Optional: Pause on hover
    container.addEventListener("mouseenter", () => clearInterval(sliderInterval));
    container.addEventListener("mouseleave", () => setInterval(nextSlide, intervalTime));
}

// --------------------
// Optional Slider CSS
// --------------------
(function injectSliderCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-slider img {
            width: 100%;
            display: block;
            border-radius: 8px;
        }

        /* Dark mode support if container has text overlays */
        body.dark-mode .spark-slider {
            color: #fff;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Clipboard Copy Function
// --------------------
function copyToClipboard(text) {
    if (!navigator.clipboard) {
        // fallback for older browsers
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed"; // avoid scrolling
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        try {
            const successful = document.execCommand('copy');
            document.body.removeChild(textarea);
            if (successful) visionToast("Copied to clipboard!");
            else visionToast("Copy failed!");
        } catch (err) {
            console.error("Copy failed:", err);
            visionToast("Copy failed!");
        }
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        visionToast("Copied to clipboard!");
    }).catch(err => {
        console.error("Copy failed:", err);
        visionToast("Copy failed!");
    });
}

// --------------------
// Password Strength Checker
// --------------------
function sparkPasswordCheck(inputSelector, barSelector) {
    const input = document.querySelector(inputSelector);
    const bar = document.querySelector(barSelector);

    if (!input || !bar) {
        console.warn("sparkPasswordCheck: Input or bar element not found.");
        return;
    }

    function checkStrength(password) {
        let score = 0;

        // Length
        if (password.length >= 8) score += 1;

        // Uppercase
        if (/[A-Z]/.test(password)) score += 1;

        // Numbers
        if (/\d/.test(password)) score += 1;

        // Symbols
        if (/[^A-Za-z0-9]/.test(password)) score += 1;

        return score;
    }

    function updateBar(score) {
        const percent = (score / 4) * 100;
        bar.style.width = percent + "%";

        // Set color
        if (score <= 1) bar.style.backgroundColor = "red";
        else if (score === 2) bar.style.backgroundColor = "orange";
        else if (score === 3) bar.style.backgroundColor = "yellow";
        else bar.style.backgroundColor = "green";
    }

    // Initialize
    updateBar(checkStrength(input.value));

    // Update on input
    input.addEventListener("input", () => {
        const score = checkStrength(input.value);
        updateBar(score);
    });
}

// --------------------
// Optional CSS Injection
// --------------------
(function injectPasswordBarCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-strength-container {
            width: 100%;
            height: 6px;
            background-color: #ddd;
            border-radius: 4px;
            margin-top: 4px;
            overflow: hidden;
        }
        .spark-strength-bar {
            height: 100%;
            width: 0;
            transition: width 0.3s ease, background-color 0.3s ease;
            border-radius: 4px;
        }

        /* Dark mode */
        body.dark-mode .spark-strength-container {
            background-color: #555;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Custom Alert Box
// --------------------
function sparkAlert(title, message, duration = 4000) {
    // Create alert background
    const alertBg = document.createElement("div");
    alertBg.className = "spark-alert-bg";

    // Create alert container
    const alertBox = document.createElement("div");
    alertBox.className = "spark-alert-box";

    // Create title
    const alertTitle = document.createElement("h3");
    alertTitle.textContent = title;

    // Create message
    const alertMsg = document.createElement("p");
    alertMsg.textContent = message;

    // Create close button
    const closeBtn = document.createElement("button");
    closeBtn.textContent = "×";
    closeBtn.className = "spark-alert-close";
    closeBtn.onclick = () => alertBg.remove();

    // Assemble alert
    alertBox.appendChild(closeBtn);
    alertBox.appendChild(alertTitle);
    alertBox.appendChild(alertMsg);
    alertBg.appendChild(alertBox);
    document.body.appendChild(alertBg);

    // Show with animation
    setTimeout(() => {
        alertBg.style.opacity = "1";
        alertBox.style.transform = "translateY(0)";
    }, 10);

    // Auto-close after duration
    setTimeout(() => {
        alertBg.style.opacity = "0";
        alertBox.style.transform = "translateY(-20px)";
        alertBg.addEventListener("transitionend", () => alertBg.remove());
    }, duration);
}

// --------------------
// Alert CSS Injection
// --------------------
(function injectAlertCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-alert-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: rgba(0,0,0,0.3);
            opacity: 0;
            transition: opacity 0.3s ease;
            z-index: 10000;
        }
        .spark-alert-box {
            background-color: #fff;
            color: #000;
            padding: 20px 30px;
            border-radius: 10px;
            max-width: 400px;
            width: 90%;
            position: relative;
            text-align: center;
            transform: translateY(-20px);
            transition: transform 0.3s ease;
            font-family: Arial, sans-serif;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .spark-alert-box h3 {
            margin: 0 0 10px 0;
        }
        .spark-alert-box p {
            margin: 0;
        }
        .spark-alert-close {
            position: absolute;
            top: 8px;
            right: 12px;
            background: none;
            border: none;
            font-size: 22px;
            cursor: pointer;
        }

        /* Dark mode support */
        body.dark-mode .spark-alert-box {
            background-color: #222;
            color: #fff;
        }
        body.dark-mode .spark-alert-bg {
            background-color: rgba(0,0,0,0.5);
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Floating Action Button (FAB)
// --------------------
function sparkFAB(mainButtonText, actions = []) {
    // Create FAB container
    const fabContainer = document.createElement("div");
    fabContainer.className = "spark-fab-container";

    // Create main FAB button
    const fabButton = document.createElement("button");
    fabButton.className = "spark-fab";
    fabButton.textContent = mainButtonText;

    // Create action menu container
    const fabMenu = document.createElement("div");
    fabMenu.className = "fab-menu";

    // Add action buttons
    actions.forEach(action => {
        const btn = document.createElement("button");
        btn.textContent = action.label;
        btn.onclick = action.onClick;
        fabMenu.appendChild(btn);
    });

    // Toggle menu on click
    fabButton.addEventListener("click", () => {
        fabMenu.classList.toggle("fab-menu-active");
    });

    // Assemble
    fabContainer.appendChild(fabButton);
    fabContainer.appendChild(fabMenu);
    document.body.appendChild(fabContainer);
}

// --------------------
// FAB CSS Injection
// --------------------
(function injectFABCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-fab-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            flex-direction: column-reverse;
            align-items: flex-end;
            z-index: 9999;
        }
        .spark-fab {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background-color: #007bff;
            color: #fff;
            border: none;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            transition: transform 0.3s;
        }
        .spark-fab:hover {
            transform: scale(1.1);
        }
        .fab-menu {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 10px;
            opacity: 0;
            pointer-events: none;
            transform: translateY(20px);
            transition: all 0.3s ease;
        }
        .fab-menu.fab-menu-active {
            opacity: 1;
            pointer-events: auto;
            transform: translateY(0);
        }
        .fab-menu button {
            padding: 10px 15px;
            border-radius: 5px;
            border: none;
            cursor: pointer;
            background-color: #333;
            color: #fff;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }
        /* Dark mode support */
        body.dark-mode .spark-fab {
            background-color: #00ffff;
            color: #000;
        }
        body.dark-mode .fab-menu button {
            background-color: #555;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Cookie Consent Popup
// --------------------
function sparkCookies(message, acceptText = "Accept") {
    // Check if already accepted
    if (localStorage.getItem("sparkCookiesAccepted")) return;

    // Create cookie banner
    const cookieBox = document.createElement("div");
    cookieBox.className = "spark-cookie-box";

    // Message
    const msg = document.createElement("span");
    msg.textContent = message;

    // Accept button
    const acceptBtn = document.createElement("button");
    acceptBtn.textContent = acceptText;
    acceptBtn.onclick = () => {
        localStorage.setItem("sparkCookiesAccepted", "true");
        cookieBox.remove();
        visionToast("Cookies accepted!");
    };

    // Assemble
    cookieBox.appendChild(msg);
    cookieBox.appendChild(acceptBtn);
    document.body.appendChild(cookieBox);
}

// --------------------
// Cookie CSS Injection
// --------------------
(function injectCookieCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-cookie-box {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0,0,0,0.85);
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 15px;
            font-family: Arial, sans-serif;
            z-index: 10000;
            animation: slideUp 0.5s ease forwards;
        }
        .spark-cookie-box button {
            background-color: #007bff;
            color: #fff;
            border: none;
            padding: 6px 12px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .spark-cookie-box button:hover {
            background-color: #0056b3;
        }

        /* Dark mode support */
        body.dark-mode .spark-cookie-box {
            background-color: rgba(255,255,255,0.1);
            color: #fff;
        }
        body.dark-mode .spark-cookie-box button {
            background-color: #00ffff;
            color: #000;
        }

        @keyframes slideUp {
            0% { transform: translateX(-50%) translateY(30px); opacity: 0; }
            100% { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Offline Detector Banner
// --------------------
function sparkOfflineBanner(message = "You are offline") {
    // Create banner
    const banner = document.createElement("div");
    banner.className = "offline-banner";
    banner.textContent = message;
    banner.style.display = "none"; // hide initially
    document.body.appendChild(banner);

    // Show banner when offline
    window.addEventListener("offline", () => {
        banner.style.display = "flex";
    });

    // Hide banner when online
    window.addEventListener("online", () => {
        banner.style.display = "none";
        visionToast("Back online!");
    });
}

// --------------------
// Offline CSS Injection
// --------------------
(function injectOfflineCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .offline-banner {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background-color: #ff4d4d;
            color: white;
            text-align: center;
            padding: 10px 0;
            font-family: Arial, sans-serif;
            font-weight: bold;
            z-index: 10000;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* Dark mode support */
        body.dark-mode .offline-banner {
            background-color: #ff6666;
        }
    `;
    document.head.appendChild(style);
})();


// --------------------
// Live Search Filter
// --------------------
function sparkFilter(inputSelector, itemSelector) {
    const input = document.querySelector(inputSelector);
    const items = document.querySelectorAll(itemSelector);

    if (!input || !items.length) {
        console.warn("sparkFilter: Input or items not found.");
        return;
    }

    input.addEventListener("input", () => {
        const query = input.value.toLowerCase();

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(query) ? "" : "none";
        });
    });
}

// --------------------
// Optional CSS Injection
// --------------------
(function injectFilterCSS() {
    const style = document.createElement("style");
    style.textContent = `
        /* Optional: highlight matching items */
        .spark-filter-highlight {
            background-color: yellow;
            transition: background-color 0.3s ease;
        }

        /* Dark mode support for items */
        body.dark-mode .item {
            color: #fff;
        }
    `;
    document.head.appendChild(style);
})();

// --------------------
// Notification Bell With Badge
// --------------------
function sparkNotify(count = 0) {
    // Check if bell exists
    let bell = document.querySelector(".spark-notify-bell");
    if (!bell) {
        // Create container
        bell = document.createElement("div");
        bell.className = "spark-notify-bell";

        // Create bell icon
        const icon = document.createElement("span");
        icon.className = "bell-icon";
        icon.innerHTML = "🔔";

        // Create badge
        const badge = document.createElement("span");
        badge.className = "bell-badge";
        badge.textContent = count;

        // Assemble
        bell.appendChild(icon);
        bell.appendChild(badge);
        document.body.appendChild(bell);
    } else {
        // Update badge count
        const badge = bell.querySelector(".bell-badge");
        badge.textContent = count;
    }
}

// --------------------
// Notification Bell CSS Injection
// --------------------
(function injectNotifyCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-notify-bell {
            position: fixed;
            top: 20px;
            right: 20px;
            font-size: 24px;
            cursor: pointer;
            z-index: 9999;
            display: flex;
            align-items: center;
        }
        .bell-badge {
            background-color: red;
            color: white;
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 50%;
            margin-left: -10px;
            margin-top: -10px;
            position: absolute;
        }

        /* Dark mode support */
        body.dark-mode .spark-notify-bell {
            color: #00ffff;
        }
        body.dark-mode .bell-badge {
            background-color: #ff5555;
        }
    `;
    document.head.appendChild(style);
})();
// --------------------
// Theme System
// --------------------
function sparkTheme(theme = {}) {
    const root = document.documentElement;

    // Default variables
    const defaultTheme = {
        primary: "#007bff",
        secondary: "#6c757d",
        background: "#ffffff",
        text: "#111111",
        accent: "#00ffff",
        danger: "#ff4d4d"
    };

    // Merge with user-defined theme
    const finalTheme = { ...defaultTheme, ...theme };

    // Apply CSS variables
    Object.keys(finalTheme).forEach(key => {
        root.style.setProperty(`--spark-${key}`, finalTheme[key]);
    });
}

// --------------------
// Optional: Inject default CSS using variables
// --------------------
(function injectThemeCSS() {
    const style = document.createElement("style");
    style.textContent = `
        body {
            background-color: var(--spark-background);
            color: var(--spark-text);
        }
        .spark-toast {
            background-color: var(--spark-primary);
        }
        .spark-fab {
            background-color: var(--spark-primary);
            color: var(--spark-text);
        }
        .spark-alert-box {
            background-color: var(--spark-background);
            color: var(--spark-text);
        }
        .fab-menu button, .spark-cookie-box button {
            background-color: var(--spark-secondary);
            color: var(--spark-text);
        }
        .bell-badge {
            background-color: var(--spark-danger);
        }
    `;
    document.head.appendChild(style);
})();
// --------------------
// Floating AI Chat Assistant
// --------------------
function sparkChatAssistant(options = {}) {
    const {
        title = "AI Assistant",
        placeholder = "Type a message...",
        themePrimary = "#007bff",
        themeText = "#fff"
    } = options;

    // Create chat container
    const chatContainer = document.createElement("div");
    chatContainer.className = "spark-chat-container";

    // Chat bubble (floating)
    const chatBubble = document.createElement("div");
    chatBubble.className = "spark-bubble";
    chatBubble.textContent = "💬";

    // Chat box
    const chatBox = document.createElement("div");
    chatBox.className = "spark-chat";

    // Chat header
    const chatHeader = document.createElement("div");
    chatHeader.className = "spark-chat-header";
    chatHeader.textContent = title;

    // Chat messages container
    const chatMessages = document.createElement("div");
    chatMessages.className = "spark-chat-messages";

    // Chat input container
    const chatInputContainer = document.createElement("div");
    chatInputContainer.className = "spark-chat-input-container";

    const chatInput = document.createElement("input");
    chatInput.type = "text";
    chatInput.placeholder = placeholder;

    const sendBtn = document.createElement("button");
    sendBtn.textContent = "Send";

    // Append input and button
    chatInputContainer.appendChild(chatInput);
    chatInputContainer.appendChild(sendBtn);

    // Assemble chat box
    chatBox.appendChild(chatHeader);
    chatBox.appendChild(chatMessages);
    chatBox.appendChild(chatInputContainer);

    // Append chat bubble and box to container
    chatContainer.appendChild(chatBubble);
    chatContainer.appendChild(chatBox);
    document.body.appendChild(chatContainer);

    // Toggle chat visibility
    chatBubble.addEventListener("click", () => {
        chatBox.classList.toggle("open");
    });

    // Send message function (placeholder)
    function sendMessage(msg) {
        if (!msg) return;
        const userMsg = document.createElement("div");
        userMsg.className = "spark-msg user";
        userMsg.textContent = msg;
        chatMessages.appendChild(userMsg);

        // AI response placeholder
        const aiMsg = document.createElement("div");
        aiMsg.className = "spark-msg ai";
        aiMsg.textContent = "AI: I'm thinking...";
        chatMessages.appendChild(aiMsg);

        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    sendBtn.addEventListener("click", () => {
        sendMessage(chatInput.value);
        chatInput.value = "";
    });

    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendMessage(chatInput.value);
            chatInput.value = "";
        }
    });
}

// --------------------
// Floating Chat CSS Injection
// --------------------
(function injectChatCSS() {
    const style = document.createElement("style");
    style.textContent = `
        .spark-chat-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            font-family: Arial, sans-serif;
        }
        .spark-bubble {
            width: 60px;
            height: 60px;
            background-color: #007bff;
            color: #fff;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }
        .spark-chat {
            width: 300px;
            max-height: 400px;
            background-color: #fff;
            color: #000;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            margin-top: 10px;
            overflow: hidden;
            display: none;
            flex-direction: column;
        }
        .spark-chat.open {
            display: flex;
        }
        .spark-chat-header {
            background-color: #007bff;
            color: #fff;
            padding: 10px;
            font-weight: bold;
            text-align: center;
        }
        .spark-chat-messages {
            flex: 1;
            padding: 10px;
            overflow-y: auto;
        }
        .spark-chat-input-container {
            display: flex;
            border-top: 1px solid #ddd;
        }
        .spark-chat-input-container input {
            flex: 1;
            padding: 8px;
            border: none;
            outline: none;
        }
        .spark-chat-input-container button {
            padding: 8px 12px;
            border: none;
            background-color: #007bff;
            color: #fff;
            cursor: pointer;
        }
        .spark-msg {
            margin-bottom: 8px;
            padding: 6px 10px;
            border-radius: 6px;
            max-width: 80%;
        }
        .spark-msg.user {
            background-color: #007bff;
            color: #fff;
            align-self: flex-end;
        }
        .spark-msg.ai {
            background-color: #f1f1f1;
            color: #000;
            align-self: flex-start;
        }

        /* Dark mode support */
        body.dark-mode .spark-chat {
            background-color: #222;
            color: #fff;
        }
        body.dark-mode .spark-chat-header {
            background-color: #00ffff;
            color: #000;
        }
        body.dark-mode .spark-msg.ai {
            background-color: #333;
            color: #fff;
        }
        body.dark-mode .spark-msg.user {
            background-color: #00ffff;
            color: #000;
        }
    `;
    document.head.appendChild(style);
})();
