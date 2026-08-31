(function () {
  'use strict';

  const SALES_EMAIL = 'znegshifan@yushiglobal.cn';
  const REQUEST_TIMEOUT_MS = 30000;
  const PRODUCT_INTERESTS = [
    'Standard CR80 Cards',
    'Custom Shape Blanks',
    'Oversized Aluminum Blanks',
    'Round & Specialty Blanks',
    'Other / Not sure'
  ];
  const ATTRIBUTION_FIELDS = [
    'utm_source',
    'utm_medium',
    'utm_campaign',
    'utm_term',
    'utm_content',
    'gclid',
    'msclkid',
    'landing_page',
    'referrer'
  ];

  const COPY = {
    en: {
      sending: 'Sending…',
      sent: '✓ Inquiry Sent!',
      successToast: "Thank you! Your inquiry was sent to our sales inbox.",
      deliveryNote: "Submit once. Our sales team will review the project details and reply by email.",
      failedToast: `We couldn't send the inquiry. Please try again or email ${SALES_EMAIL}.`,
      timeoutToast: `The request timed out. Please try again or email ${SALES_EMAIL}.`,
      inProgressToast: 'Your first submission is still being delivered. Please wait a moment before retrying.',
      rateLimitToast: 'Too many attempts. Please wait a few minutes and try again.',
      invalidToast: 'Please check the required fields and try again.'
    },
    ro: {
      sending: 'Se trimite…',
      sent: '✓ Cerere trimisă!',
      successToast: 'Vă mulțumim! Cererea a fost trimisă în căsuța echipei noastre de vânzări.',
      deliveryNote: 'Trimiteți formularul o singură dată. Echipa noastră va analiza proiectul și va răspunde prin e-mail.',
      failedToast: `Cererea nu a putut fi trimisă. Încercați din nou sau scrieți la ${SALES_EMAIL}.`,
      timeoutToast: `Solicitarea a expirat. Încercați din nou sau scrieți la ${SALES_EMAIL}.`,
      inProgressToast: 'Prima trimitere este încă în curs. Așteptați puțin înainte de a încerca din nou.',
      rateLimitToast: 'Prea multe încercări. Așteptați câteva minute și încercați din nou.',
      invalidToast: 'Verificați câmpurile obligatorii și încercați din nou.'
    },
    pl: {
      sending: 'Wysyłanie…',
      sent: '✓ Zapytanie wysłane!',
      successToast: 'Dziękujemy! Zapytanie zostało wysłane do naszej skrzynki sprzedażowej.',
      deliveryNote: 'Wyślij formularz tylko raz. Nasz zespół przeanalizuje projekt i odpowie e-mailem.',
      failedToast: `Nie udało się wysłać zapytania. Spróbuj ponownie lub napisz na ${SALES_EMAIL}.`,
      timeoutToast: `Upłynął limit czasu. Spróbuj ponownie lub napisz na ${SALES_EMAIL}.`,
      inProgressToast: 'Pierwsze zgłoszenie jest nadal wysyłane. Odczekaj chwilę przed ponowną próbą.',
      rateLimitToast: 'Zbyt wiele prób. Odczekaj kilka minut i spróbuj ponownie.',
      invalidToast: 'Sprawdź wymagane pola i spróbuj ponownie.'
    }
  };

  let toastTimer;

  function getLanguage() {
    return (document.documentElement.lang || 'en').toLowerCase().split('-')[0];
  }

  function getCopy() {
    return COPY[getLanguage()] || COPY.en;
  }

  function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('is-visible');
    toastTimer = window.setTimeout(() => {
      toast.classList.remove('is-visible');
    }, 6000);
  }

  function setButtonState(button, text, busy) {
    button.textContent = text;
    button.disabled = busy;
    button.setAttribute('aria-busy', busy ? 'true' : 'false');
    button.style.opacity = busy ? '0.7' : '';
    if (!busy) {
      button.style.background = '';
      button.style.color = '';
    }
  }

  function errorMessage(copy, code, timedOut) {
    if (timedOut) return copy.timeoutToast;
    if (code === 'submission_in_progress') return copy.inProgressToast;
    if (code === 'rate_limited') return copy.rateLimitToast;
    if (
      [
        'invalid_email',
        'invalid_input',
        'input_too_long',
        'input_too_short',
        'missing_required'
      ].includes(code)
    ) {
      return copy.invalidToast;
    }
    return copy.failedToast;
  }

  function getSubmissionId(form) {
    if (form.dataset.submissionId) return form.dataset.submissionId;

    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      form.dataset.submissionId = window.crypto.randomUUID();
    } else {
      const randomPart = Math.random().toString(36).slice(2).padEnd(16, '0').slice(0, 16);
      form.dataset.submissionId = `${Date.now().toString(36)}-${randomPart}-${randomPart}`;
    }
    return form.dataset.submissionId;
  }

  function addAttribution(formData) {
    const marketing = window.AlumCraftMarketing;
    if (!marketing || typeof marketing.getAttribution !== 'function') return;

    let attribution = {};
    try {
      attribution = marketing.getAttribution() || {};
    } catch (_error) {
      // Attribution is optional and must never prevent an inquiry from being sent.
    }

    ATTRIBUTION_FIELDS.forEach((field) => {
      if (typeof attribution[field] === 'string' && attribution[field]) {
        formData.set(field, attribution[field]);
      }
    });
  }

  function dispatchInquirySuccess(form, formData, submissionId) {
    if (form.dataset.successEventId === submissionId) return;
    form.dataset.successEventId = submissionId;

    const productInterest = String(formData.get('product_interest') || '');
    document.dispatchEvent(
      new CustomEvent('alumcraft:inquiry-success', {
        detail: {
          form_id: form.id || 'inquiry-form',
          product_interest: PRODUCT_INTERESTS.includes(productInterest) ? productInterest : '',
          page_language: getLanguage()
        }
      })
    );
  }

  window.handleSubmit = async function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('.form-submit');
    const copy = getCopy();

    if (!form.reportValidity() || button.disabled) return;
    button.dataset.idleLabel = button.dataset.idleLabel || button.textContent;
    setButtonState(button, copy.sending, true);

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    const formData = new FormData(form);
    formData.delete('form-name');
    formData.set('language', getLanguage());
    formData.set('source_page', window.location.href);
    const submissionId = getSubmissionId(form);
    formData.set('submission_id', submissionId);
    addAttribution(formData);

    try {
      const response = await fetch(form.getAttribute('action') || '/api/inquiry', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        },
        body: new URLSearchParams(formData).toString(),
        credentials: 'same-origin',
        signal: controller.signal
      });

      let result = {};
      try {
        result = await response.json();
      } catch (_error) {
        // An invalid server response is handled as a failed submission below.
      }

      if (!response.ok || result.ok !== true) {
        const submissionError = new Error('Inquiry delivery failed');
        submissionError.code = result.code || 'delivery_failed';
        throw submissionError;
      }

      dispatchInquirySuccess(form, formData, submissionId);
      delete form.dataset.submissionId;
      form.reset();
      button.textContent = copy.sent;
      button.style.background = '#4ade80';
      button.style.color = '#0d0d0d';
      showToast(copy.successToast);
      window.setTimeout(() => setButtonState(button, button.dataset.idleLabel, false), 3000);
    } catch (error) {
      console.error('Inquiry form submission failed:', error);
      setButtonState(button, button.dataset.idleLabel, false);
      showToast(errorMessage(copy, error.code, error.name === 'AbortError'));
    } finally {
      window.clearTimeout(timeout);
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('inquiry-form');
    if (!form) return;

    const productSelect = form.querySelector('[name="product_interest"]');
    if (productSelect) {
      const requestedProduct = new URLSearchParams(window.location.search).get('product');
      const isAvailableOption = Array.from(productSelect.options).some(
        (option) => option.value === requestedProduct
      );
      if (requestedProduct && PRODUCT_INTERESTS.includes(requestedProduct) && isAvailableOption) {
        productSelect.value = requestedProduct;
      }

      document.querySelectorAll('[data-product-interest]').forEach((link) => {
        link.addEventListener('click', () => {
          productSelect.value = link.dataset.productInterest || '';
        });
      });
    }

    const note = document.getElementById('form-delivery-note');
    if (note) note.textContent = getCopy().deliveryNote;
  });
})();
