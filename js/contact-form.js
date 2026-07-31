(function () {
  'use strict';

  const SALES_EMAIL = 'znegshifan@yushiglobal.cn';
  const NETLIFY_HOST_SUFFIX = '.netlify.app';

  const COPY = {
    en: {
      sending: 'Sending…',
      sent: '✓ Inquiry Sent!',
      openingEmail: 'Opening email app…',
      successToast: "Thank you! We'll be in touch within 24 hours.",
      emailToast: 'Your email draft is ready. Please review it and press Send.',
      emailNote: "Submitting here opens your email app with the inquiry details. We'll reply within 24 hours.",
      fallbackToast: 'The online form was unavailable, so we opened an email draft instead.'
    },
    ro: {
      sending: 'Se trimite…',
      sent: '✓ Cerere trimisă!',
      openingEmail: 'Se deschide aplicația de e-mail…',
      successToast: 'Vă mulțumim! Vă vom contacta în termen de 24 de ore.',
      emailToast: 'Mesajul este pregătit în aplicația de e-mail. Verificați-l și apăsați Trimiteți.',
      emailNote: 'Trimiterea de aici deschide aplicația de e-mail cu detaliile cererii. Vă răspundem în 24 de ore.',
      fallbackToast: 'Formularul online nu a fost disponibil, așa că am deschis un mesaj e-mail.'
    },
    pl: {
      sending: 'Wysyłanie…',
      sent: '✓ Zapytanie wysłane!',
      openingEmail: 'Otwieranie programu pocztowego…',
      successToast: 'Dziękujemy! Skontaktujemy się w ciągu 24 godzin.',
      emailToast: 'Wiadomość jest gotowa w programie pocztowym. Sprawdź ją i kliknij Wyślij.',
      emailNote: 'Wysłanie formularza otworzy program pocztowy z treścią zapytania. Odpowiemy w ciągu 24 godzin.',
      fallbackToast: 'Formularz online był niedostępny, dlatego otworzyliśmy wiadomość e-mail.'
    }
  };

  let toastTimer;

  function getCopy() {
    const language = (document.documentElement.lang || 'en').toLowerCase().split('-')[0];
    return COPY[language] || COPY.en;
  }

  function isNetlifyRuntime() {
    return window.location.hostname.toLowerCase().endsWith(NETLIFY_HOST_SUFFIX);
  }

  function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.classList.add('is-visible');
    toastTimer = window.setTimeout(() => {
      toast.classList.remove('is-visible');
    }, 4500);
  }

  function setButtonState(button, text, busy) {
    button.textContent = text;
    button.disabled = busy;
    button.style.opacity = busy ? '0.7' : '';
    if (!busy) {
      button.style.background = '';
      button.style.color = '';
    }
  }

  function buildEmailDraft(form) {
    const data = new FormData(form);
    const name = String(data.get('name') || '').trim();
    const company = String(data.get('company') || '').trim();
    const subject = `AlumCraft inquiry from ${name}${company ? ` — ${company}` : ''}`;
    const fields = [
      ['Name', name],
      ['Company', company],
      ['Email', data.get('email')],
      ['Country', data.get('country')],
      ['Product interest', data.get('product_interest')],
      ['Quantity', data.get('quantity')],
      ['Project details', data.get('message')],
      ['Website language', document.documentElement.lang || 'en'],
      ['Source page', window.location.href]
    ];
    const body = fields
      .filter(([, value]) => String(value || '').trim())
      .map(([label, value]) => `${label}: ${String(value).trim()}`)
      .join('\n\n');

    return `mailto:${SALES_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  }

  function openEmailDraft(form, copy, fallback) {
    const button = form.querySelector('.form-submit');
    setButtonState(button, copy.openingEmail, true);
    showToast(fallback ? copy.fallbackToast : copy.emailToast);
    window.location.href = buildEmailDraft(form);
    window.setTimeout(() => setButtonState(button, button.dataset.idleLabel, false), 1500);
  }

  window.handleSubmit = async function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('.form-submit');
    const copy = getCopy();

    if (!form.reportValidity()) return;
    button.dataset.idleLabel = button.dataset.idleLabel || button.textContent;

    if (!isNetlifyRuntime()) {
      openEmailDraft(form, copy, false);
      return;
    }

    setButtonState(button, copy.sending, true);

    try {
      const response = await fetch(form.getAttribute('action') || window.location.pathname || '/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body: new URLSearchParams(new FormData(form)).toString()
      });

      if (!response.ok) {
        throw new Error(`Inquiry form returned HTTP ${response.status}`);
      }

      form.reset();
      button.textContent = copy.sent;
      button.style.background = '#4ade80';
      button.style.color = '#0d0d0d';
      showToast(copy.successToast);
      window.setTimeout(() => setButtonState(button, button.dataset.idleLabel, false), 3000);
    } catch (error) {
      console.error('Inquiry form submission failed:', error);
      openEmailDraft(form, copy, true);
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('inquiry-form');
    if (!form) return;

    const productSelect = form.querySelector('[name="product_interest"]');
    if (productSelect) {
      document.querySelectorAll('[data-product-interest]').forEach((link) => {
        link.addEventListener('click', () => {
          productSelect.value = link.dataset.productInterest || '';
        });
      });
    }

    if (isNetlifyRuntime()) return;

    const note = document.getElementById('form-delivery-note');
    if (note) note.textContent = getCopy().emailNote;
  });
})();
