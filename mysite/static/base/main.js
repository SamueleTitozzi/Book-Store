// ======================================================
// 🔹 UTILS (допоміжні функції)
// ======================================================

function getCookie(name) {
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');

        for (let cookie of cookies) {
            cookie = cookie.trim();

            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }

    return cookieValue;
}


// ======================================================
// 🔹 CART (додавання в кошик)
// ======================================================

function initCart() {
    const csrftoken = getCookie('csrftoken');

    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.add-to-cart-btn');
        if (!btn) return;

        e.preventDefault();

        const url = btn.dataset.url;

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const badge = document.getElementById('cart-count');
                if (badge) badge.innerText = data.count;

                btn.innerText = "✓ Додано";
                setTimeout(() => btn.innerText = "🛒 Купити", 800);
            }
        });
    });
}


// ======================================================
// 🔹 LIVE SEARCH
// ======================================================

function initLiveSearch() {
    const input = document.getElementById("searchInput");
    const resultsBox = document.getElementById("live-search-results");

    if (!input || !resultsBox) return;

    const liveSearchUrl = input.dataset.liveSearchUrl;
    let timeout = null;

    input.addEventListener("input", function () {
        clearTimeout(timeout);

        timeout = setTimeout(() => {
            const query = input.value.trim();

            if (!query) {
                resultsBox.innerHTML = "";
                return;
            }

            fetch(liveSearchUrl + '?q=' + encodeURIComponent(query))
                .then(res => res.json())
                .then(data => {
                    resultsBox.innerHTML = "";

                    if (!data.results.length) {
                        resultsBox.innerHTML = `<div>Нічого не знайдено</div>`;
                        return;
                    }

                    data.results.forEach(book => {
                        const item = document.createElement("a");
                        item.classList.add("live-search-item");
                        item.href = `/book/${book.id}/`;

                        item.innerHTML = `
                            <img src="${book.image}" class="live-search-image">
                            <span class="live-search-title">${book.title}</span>
                        `;

                        resultsBox.appendChild(item);
                    });
                });
        }, 300);
    });

    document.addEventListener("click", function (e) {
        if (!e.target.closest("form")) {
            resultsBox.innerHTML = "";
        }
    });
}


// ======================================================
// 🔹 STRIPE (оплата)
// ======================================================

function initStripe() {
    const cardContainer = document.getElementById("card-element");
    const payButton = document.getElementById("pay-button");

    if (!cardContainer || !payButton) return;

    const stripePublicKey = cardContainer.dataset.stripeKey;

    const stripe = Stripe(stripePublicKey);
    const elements = stripe.elements();
    const cardElement = elements.create("card");

    cardElement.mount("#card-element");

    payButton.addEventListener("click", async function () {

        payButton.disabled = true;
        payButton.innerText = "Обробка...";

        try {
            // 🔹 1. створення PaymentIntent
            const response = await fetch("/orders/create-payment/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                }
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // 🔹 2. підтвердження платежу
            const result = await stripe.confirmCardPayment(data.client_secret, {
                payment_method: {
                    card: cardElement
                }
            });

            if (result.error) {
                document.getElementById("card-errors").innerText = result.error.message;
                throw new Error(result.error.message);
            }

            // 🔥 3. просто редірект (нічого НЕ оновлюємо)
            if (result.paymentIntent.status === "succeeded") {

                await fetch(`/orders/confirm-payment/${data.order_id}/`, {
                method: "POST",
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                }
                });

                payButton.innerText = "Успішно!";
                payButton.disabled = true;

                setTimeout(() => {
                    window.location.href = `/orders/confirmation/${data.order_id}/`;
                }, 800);
            }

        } catch (error) {
            console.error(error);

            payButton.disabled = false;
            payButton.innerText = "Оплатити";
        }
    });
}

function initPaymentToggle() {
    const select = document.querySelector('[name="payment_method"]');
    const stripeBlock = document.getElementById('stripe-block');

    if (!select || !stripeBlock) return;

    function toggle() {
        if (select.value === 'stripe') {
            stripeBlock.style.display = 'block';
        } else {
            stripeBlock.style.display = 'none';
        }
    }

    toggle();
    select.addEventListener('change', toggle);
}

function initStripeModal() {
    const modal = document.getElementById("stripe-modal");

    // якщо нема — виходимо
    if (!modal) return;

    // 🔥 якщо бекенд сказав "order_confirmed"
    const container = document.querySelector('.checkout-container');
    const shouldOpen = container?.dataset.openStripe;

    if (shouldOpen === "true") {
        modal.classList.add("active");
    }

    // закриття
    const closeBtn = document.getElementById("close-modal");

    closeBtn.addEventListener("click", () => {
        modal.classList.remove("active");
    });

    // клік поза модалкою
    modal.addEventListener("click", (e) => {
        if (e.target === modal) {
            modal.classList.remove("active");
        }
    });
}
// ======================================================
// 🔹 ORDER STATUS CHECK (confirmation page)
// ======================================================

function initOrderStatusChecker() {
    const el = document.getElementById("order-status");
    if (!el) return;

    const orderId = el.dataset.orderId;

    const loading = document.getElementById("status-loading");
    const success = document.getElementById("status-success");
    const failed = document.getElementById("status-failed");

    let attempts = 0;
    const maxAttempts = 20;

    const interval = setInterval(async () => {
        attempts++;

        try {
            const res = await fetch(`/orders/check-status/${orderId}/`);
            const data = await res.json();

            if (data.status === "paid" || data.status === "processing") {
                loading.style.display = "none";
                success.style.display = "block";
                clearInterval(interval);

                setTimeout(() => {
                    window.location.href = "/orders/history/";
                }, 5000);
            }

            if (data.status === "cancelled") {
                loading.style.display = "none";
                failed.style.display = "block";
                clearInterval(interval);
            }

            if (data.status === "processing") {
                success.innerHTML = `
                <div class="confirmation-icon">📦</div>
                <h2>Замовлення прийнято!</h2>
                <p>Ми зв'яжемось з вами найближчим часом</p>

                <div class="confirmation-actions">
                    <a href="/orders/history/" class="btn-primary">
                        📚 Мої замовлення
                    </a>

                    <a href="/" class="btn-secondary">
                        🛍 Продовжити покупки
                    </a>
                </div>
                `;
            }

        } catch (e) {
            console.error(e);
        }

        if (attempts >= maxAttempts) {
            loading.innerHTML = `
                <h2>⚠️ Затримка підтвердження</h2>
                <p>Спробуйте оновити сторінку</p>
            `;
            clearInterval(interval);
        }

    }, 1500);
}

function initCheckoutFlow() {
    const form = document.getElementById("checkout-form");
    const modal = document.getElementById("stripe-modal");
    const paymentSelect = document.querySelector('[name="payment_method"]');

    if (!form || !modal || !paymentSelect) return;

    form.addEventListener("submit", function (e) {

        if (paymentSelect.value === "stripe") {
            e.preventDefault(); // ❗ блокуємо submit

            // 🔥 спочатку зберігаємо форму
            fetch("", {
                method: "POST",
                body: new FormData(form)
            })
            .then(res => res.text())
            .then(() => {
                // 🔥 відкриваємо modal
                modal.classList.add("active");
            });
        }

    });

    // закриття
    document.getElementById("close-modal").addEventListener("click", () => {
        modal.classList.remove("active");
    });
}


// ======================================================
// 🚀 INIT (запуск всього)
// ======================================================

document.addEventListener("DOMContentLoaded", function () {
    initCart();
    initLiveSearch();
    initStripe();
    initOrderStatusChecker();
    initPaymentToggle();
    initStripeModal();
    initCheckoutFlow();
});