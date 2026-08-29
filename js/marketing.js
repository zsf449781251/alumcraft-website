(function () {
  'use strict';

  if (window.AlumCraftMarketing && window.AlumCraftMarketing.__initialized) return;

  const CONSENT_STORAGE_KEY = 'alumcraft_consent_v1';
  const ATTRIBUTION_STORAGE_KEY = 'alumcraft_attribution_v1';
  const CONSENT_VERSION = String(
    (window.AlumCraftMarketingConfig && window.AlumCraftMarketingConfig.privacyVersion) || '1'
  );
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
  const QUERY_ATTRIBUTION_FIELDS = ATTRIBUTION_FIELDS.slice(0, 7);

  const COPY = {
    en: {
      title: 'Your privacy choices',
      summary: 'We use optional analytics and advertising cookies only with your permission. The website and inquiry form work if you reject them.',
      privacy: 'Privacy & Cookies',
      accept: 'Accept all',
      reject: 'Reject non-essential',
      settings: 'Cookie settings',
      settingsTitle: 'Choose your cookie settings',
      settingsSummary: 'Necessary storage keeps your privacy choice. Optional categories stay off until you enable them.',
      analyticsTitle: 'Analytics',
      analyticsDescription: 'Helps us understand visits and inquiry journeys without sending form details.',
      adsTitle: 'Advertising',
      adsDescription: 'Helps us measure campaign performance and avoid showing irrelevant advertising.',
      necessary: 'Necessary storage is always active.',
      save: 'Save choices',
      back: 'Back',
      launcher: 'Cookie settings'
    },
    ro: {
      title: 'Opțiunile dvs. de confidențialitate',
      summary: 'Folosim cookie-uri opționale pentru analiză și publicitate numai cu acordul dvs. Site-ul și formularul de cerere funcționează și dacă le refuzați.',
      privacy: 'Confidențialitate și cookie-uri',
      accept: 'Acceptă toate',
      reject: 'Respinge opționalele',
      settings: 'Setări cookie',
      settingsTitle: 'Alegeți setările cookie',
      settingsSummary: 'Stocarea necesară păstrează alegerea dvs. Categoriile opționale rămân oprite până când le activați.',
      analyticsTitle: 'Analiză',
      analyticsDescription: 'Ne ajută să înțelegem vizitele și traseul către cerere, fără a trimite detaliile formularului.',
      adsTitle: 'Publicitate',
      adsDescription: 'Ne ajută să măsurăm campaniile și să evităm publicitatea nerelevantă.',
      necessary: 'Stocarea necesară este mereu activă.',
      save: 'Salvează alegerile',
      back: 'Înapoi',
      launcher: 'Setări cookie'
    },
    pl: {
      title: 'Twoje ustawienia prywatności',
      summary: 'Opcjonalnych plików cookie do analityki i reklam używamy wyłącznie za Twoją zgodą. Witryna i formularz zapytania działają także po ich odrzuceniu.',
      privacy: 'Prywatność i pliki cookie',
      accept: 'Akceptuj wszystkie',
      reject: 'Odrzuć opcjonalne',
      settings: 'Ustawienia cookie',
      settingsTitle: 'Wybierz ustawienia cookie',
      settingsSummary: 'Niezbędna pamięć zachowuje Twój wybór. Kategorie opcjonalne pozostają wyłączone, dopóki ich nie włączysz.',
      analyticsTitle: 'Analityka',
      analyticsDescription: 'Pomaga nam zrozumieć wizyty i drogę do zapytania bez przesyłania treści formularza.',
      adsTitle: 'Reklamy',
      adsDescription: 'Pomaga mierzyć kampanie i ograniczać nietrafne reklamy.',
      necessary: 'Niezbędna pamięć jest zawsze aktywna.',
      save: 'Zapisz wybór',
      back: 'Wstecz',
      launcher: 'Ustawienia cookie'
    }
  };

  let activeConsent = readConsent();
  let dialog;
  let mainPanel;
  let settingsPanel;
  let analyticsToggle;
  let adsToggle;
  let previouslyFocused;
  let googleTagInitialized = false;

  function getLocale() {
    const locale = (document.documentElement.lang || 'en').toLowerCase().split('-')[0];
    return Object.prototype.hasOwnProperty.call(COPY, locale) ? locale : 'en';
  }

  function getCopy() {
    return COPY[getLocale()];
  }

  function privacyPath() {
    const locale = getLocale();
    return locale === 'en' ? '/privacy.html' : `/${locale}/privacy.html`;
  }

  function safeRead(storage, key) {
    try {
      return storage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function safeWrite(storage, key, value) {
    try {
      storage.setItem(key, value);
      return true;
    } catch (_error) {
      return false;
    }
  }

  function safeRemove(storage, key) {
    try {
      storage.removeItem(key);
    } catch (_error) {
      // Storage can be unavailable in privacy-restricted browser contexts.
    }
  }

  function normalizeConsent(value) {
    if (!value || typeof value !== 'object') return null;
    if (value.version !== CONSENT_VERSION) return null;
    if (typeof value.analytics !== 'boolean' || typeof value.ads !== 'boolean') return null;
    if (typeof value.timestamp !== 'string' || typeof value.locale !== 'string') return null;

    return {
      version: CONSENT_VERSION,
      locale: value.locale,
      timestamp: value.timestamp,
      analytics: value.analytics,
      ads: value.ads
    };
  }

  function readConsent() {
    const raw = safeRead(window.localStorage, CONSENT_STORAGE_KEY);
    if (!raw) return null;

    try {
      return normalizeConsent(JSON.parse(raw));
    } catch (_error) {
      return null;
    }
  }

  function storeConsent(analytics, ads) {
    const nextConsent = {
      version: CONSENT_VERSION,
      locale: getLocale(),
      timestamp: new Date().toISOString(),
      analytics: Boolean(analytics),
      ads: Boolean(ads)
    };
    safeWrite(window.localStorage, CONSENT_STORAGE_KEY, JSON.stringify(nextConsent));
    activeConsent = nextConsent;
    return nextConsent;
  }

  function sanitizeText(value, maxLength) {
    return String(value || '')
      .replace(/[\u0000-\u001f\u007f]/g, '')
      .trim()
      .slice(0, maxLength);
  }

  function sanitizeUrl(value) {
    if (!value) return '';

    try {
      const parsed = new URL(value, window.location.origin);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
      return `${parsed.origin}${parsed.pathname}`.slice(0, 500);
    } catch (_error) {
      return '';
    }
  }

  function sanitizeReferrer(value) {
    if (!value) return '';

    try {
      const parsed = new URL(value, window.location.origin);
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
      if (parsed.origin !== window.location.origin) return parsed.origin.slice(0, 500);
      return `${parsed.origin}${parsed.pathname}`.slice(0, 500);
    } catch (_error) {
      return '';
    }
  }

  function readAttribution() {
    const raw = safeRead(window.sessionStorage, ATTRIBUTION_STORAGE_KEY);
    if (!raw) return {};

    try {
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {};

      return ATTRIBUTION_FIELDS.reduce((result, field) => {
        if (typeof parsed[field] === 'string' && parsed[field]) result[field] = parsed[field];
        return result;
      }, {});
    } catch (_error) {
      return {};
    }
  }

  function captureAttribution() {
    if (!activeConsent || activeConsent.analytics !== true) return {};

    const attribution = readAttribution();
    const parameters = new URLSearchParams(window.location.search);

    QUERY_ATTRIBUTION_FIELDS.forEach((field) => {
      if (!parameters.has(field)) return;
      const value = sanitizeText(parameters.get(field), 200);
      if (value) attribution[field] = value;
    });

    if (!attribution.landing_page) attribution.landing_page = sanitizeUrl(window.location.href);
    if (!attribution.referrer) attribution.referrer = sanitizeReferrer(document.referrer);
    if (!attribution.referrer) delete attribution.referrer;

    safeWrite(window.sessionStorage, ATTRIBUTION_STORAGE_KEY, JSON.stringify(attribution));
    return attribution;
  }

  function getAttribution() {
    if (!activeConsent || activeConsent.analytics !== true) return {};
    const attribution = captureAttribution();
    return ATTRIBUTION_FIELDS.reduce((result, field) => {
      if (attribution[field]) result[field] = attribution[field];
      return result;
    }, {});
  }

  function getGoogleTagId() {
    const config = window.AlumCraftMarketingConfig;
    const tagId = config && typeof config.googleTagId === 'string' ? config.googleTagId.trim() : '';
    return /^(G|AW|DC)-[A-Z0-9-]+$/i.test(tagId) ? tagId : '';
  }

  function consentSignals(consent) {
    const analytics = consent && consent.analytics ? 'granted' : 'denied';
    const ads = consent && consent.ads ? 'granted' : 'denied';
    return {
      analytics_storage: analytics,
      ad_storage: ads,
      ad_user_data: ads,
      ad_personalization: ads
    };
  }

  function queueGoogleConsent(command, consent) {
    if (typeof window.gtag !== 'function') return;
    const signals = consentSignals(consent);
    if (command === 'default') signals.ads_data_redaction = true;
    window.gtag('consent', command, signals);
  }

  function initializeGoogleTag(consent) {
    if (googleTagInitialized || (!consent.analytics && !consent.ads)) return;

    const googleTagId = getGoogleTagId();
    if (!googleTagId) return;

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () {
      window.dataLayer.push(arguments);
    };

    queueGoogleConsent('default', { analytics: false, ads: false });
    window.gtag('set', 'ads_data_redaction', true);
    queueGoogleConsent('update', consent);
    window.gtag('js', new Date());
    window.gtag('config', googleTagId, {
      anonymize_ip: true,
      send_page_view: consent.analytics === true
    });

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(googleTagId)}`;
    script.dataset.alumcraftGoogleTag = googleTagId;
    document.head.appendChild(script);
    googleTagInitialized = true;
  }

  function applyConsent(consent) {
    if (consent.analytics) {
      captureAttribution();
    } else {
      safeRemove(window.sessionStorage, ATTRIBUTION_STORAGE_KEY);
    }

    if (googleTagInitialized) {
      queueGoogleConsent('update', consent);
    } else {
      initializeGoogleTag(consent);
    }
  }

  function sanitizeEventParameters(parameters) {
    if (!parameters || typeof parameters !== 'object' || Array.isArray(parameters)) return {};

    const sensitiveKey = /(email|phone|mobile|name|company|message|address|detail|content)/i;
    return Object.keys(parameters).slice(0, 20).reduce((result, key) => {
      if (sensitiveKey.test(key)) return result;
      const safeKey = sanitizeText(key, 40).replace(/[^a-zA-Z0-9_]/g, '_');
      if (!safeKey) return result;

      const value = parameters[key];
      if (typeof value === 'boolean' || (typeof value === 'number' && Number.isFinite(value))) {
        result[safeKey] = value;
      } else if (typeof value === 'string') {
        const safeValue = sanitizeText(value, 100);
        if (safeValue) result[safeKey] = safeValue;
      }
      return result;
    }, {});
  }

  function trackEvent(eventName, parameters) {
    if (!activeConsent || activeConsent.analytics !== true) return false;
    if (!googleTagInitialized || typeof window.gtag !== 'function') return false;

    const safeName = sanitizeText(eventName, 40).replace(/[^a-zA-Z0-9_]/g, '_');
    if (!safeName) return false;
    window.gtag('event', safeName, sanitizeEventParameters(parameters));
    return true;
  }

  function setPanel(panel) {
    if (!dialog) return;
    const showSettings = panel === 'settings';
    mainPanel.hidden = showSettings;
    settingsPanel.hidden = !showSettings;
    dialog.setAttribute('aria-labelledby', showSettings ? 'ac-consent-settings-title' : 'ac-consent-title');

    if (showSettings) {
      const current = activeConsent || { analytics: false, ads: false };
      analyticsToggle.checked = current.analytics;
      adsToggle.checked = current.ads;
    }
  }

  function showDialog(panel) {
    if (!dialog) return;
    previouslyFocused = document.activeElement;
    setPanel(panel || 'main');
    dialog.hidden = false;
    document.documentElement.classList.add('ac-consent-open');
    window.requestAnimationFrame(() => {
      dialog.classList.add('is-visible');
      const heading = dialog.querySelector(panel === 'settings' ? '#ac-consent-settings-title' : '#ac-consent-title');
      if (heading) heading.focus();
    });
  }

  function hideDialog() {
    if (!dialog) return;
    dialog.classList.remove('is-visible');
    document.documentElement.classList.remove('ac-consent-open');
    window.setTimeout(() => {
      if (!dialog.classList.contains('is-visible')) dialog.hidden = true;
    }, 180);
    if (previouslyFocused && typeof previouslyFocused.focus === 'function') previouslyFocused.focus();
  }

  function saveChoice(analytics, ads) {
    const consent = storeConsent(analytics, ads);
    applyConsent(consent);
    hideDialog();
    document.dispatchEvent(new CustomEvent('alumcraft:consent-updated', { detail: { ...consent } }));
  }

  function openSettings() {
    showDialog('settings');
  }

  function createDialog() {
    const copy = getCopy();
    dialog = document.createElement('aside');
    dialog.className = 'ac-consent-dialog';
    dialog.id = 'ac-consent-dialog';
    dialog.hidden = true;
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'ac-consent-title');
    dialog.innerHTML = `
      <div class="ac-consent-surface">
        <section class="ac-consent-panel" data-consent-main>
          <div class="ac-consent-copy">
            <h2 id="ac-consent-title" tabindex="-1">${copy.title}</h2>
            <p>${copy.summary}</p>
            <a href="${privacyPath()}">${copy.privacy}</a>
          </div>
          <div class="ac-consent-actions" aria-label="${copy.title}">
            <button type="button" data-consent-accept>${copy.accept}</button>
            <button type="button" data-consent-reject>${copy.reject}</button>
            <button type="button" data-consent-open-settings>${copy.settings}</button>
          </div>
        </section>
        <section class="ac-consent-panel ac-consent-preferences" data-consent-preferences hidden>
          <div class="ac-consent-copy">
            <h2 id="ac-consent-settings-title" tabindex="-1">${copy.settingsTitle}</h2>
            <p>${copy.settingsSummary}</p>
            <p class="ac-consent-necessary">${copy.necessary}</p>
          </div>
          <div class="ac-consent-categories">
            <label class="ac-consent-category">
              <span><strong>${copy.analyticsTitle}</strong><small>${copy.analyticsDescription}</small></span>
              <input type="checkbox" data-consent-analytics>
              <i aria-hidden="true"></i>
            </label>
            <label class="ac-consent-category">
              <span><strong>${copy.adsTitle}</strong><small>${copy.adsDescription}</small></span>
              <input type="checkbox" data-consent-ads>
              <i aria-hidden="true"></i>
            </label>
          </div>
          <div class="ac-consent-actions ac-consent-settings-actions">
            <button type="button" data-consent-save>${copy.save}</button>
            <button type="button" data-consent-back>${copy.back}</button>
          </div>
        </section>
      </div>`;

    document.body.appendChild(dialog);
    mainPanel = dialog.querySelector('[data-consent-main]');
    settingsPanel = dialog.querySelector('[data-consent-preferences]');
    analyticsToggle = dialog.querySelector('[data-consent-analytics]');
    adsToggle = dialog.querySelector('[data-consent-ads]');

    dialog.querySelector('[data-consent-accept]').addEventListener('click', () => saveChoice(true, true));
    dialog.querySelector('[data-consent-reject]').addEventListener('click', () => saveChoice(false, false));
    dialog.querySelector('[data-consent-open-settings]').addEventListener('click', openSettings);
    dialog.querySelector('[data-consent-save]').addEventListener('click', () => {
      saveChoice(analyticsToggle.checked, adsToggle.checked);
    });
    dialog.querySelector('[data-consent-back]').addEventListener('click', () => setPanel('main'));
  }

  function createSettingsLauncher() {
    const launcher = document.createElement('button');
    launcher.type = 'button';
    launcher.className = 'ac-consent-launcher';
    launcher.dataset.consentSettings = '';
    launcher.textContent = getCopy().launcher;
    launcher.setAttribute('aria-controls', 'ac-consent-dialog');
    document.body.appendChild(launcher);
  }

  function injectFooterControls() {
    const footer = document.querySelector('footer');
    if (!footer || footer.querySelector('[data-consent-footer], [data-consent-settings]')) return;

    const copy = getCopy();
    const controls = document.createElement('span');
    controls.className = 'ac-consent-footer-controls';
    controls.dataset.consentFooter = '';

    const privacyLink = document.createElement('a');
    privacyLink.href = privacyPath();
    privacyLink.textContent = copy.privacy;

    const settingsButton = document.createElement('button');
    settingsButton.type = 'button';
    settingsButton.dataset.consentSettings = '';
    settingsButton.textContent = copy.launcher;
    settingsButton.setAttribute('aria-controls', 'ac-consent-dialog');

    controls.append(privacyLink, settingsButton);
    const target = footer.querySelector('.footer-links, .footer-left') || footer;
    target.appendChild(controls);
  }

  function contactMethod(link) {
    const href = link.getAttribute('href') || '';
    if (/^mailto:/i.test(href)) return 'email';
    try {
      const hostname = new URL(href, window.location.href).hostname.toLowerCase();
      if (hostname === 'wa.me' || hostname.endsWith('.whatsapp.com') || hostname === 'whatsapp.com') {
        return 'whatsapp';
      }
    } catch (_error) {
      return '';
    }
    return '';
  }

  function handleDocumentClick(event) {
    const settingsControl = event.target.closest('[data-consent-settings]');
    if (settingsControl) {
      event.preventDefault();
      openSettings();
      return;
    }

    const link = event.target.closest('a[href]');
    if (!link) return;
    const method = contactMethod(link);
    if (!method) return;

    trackEvent(`${method}_click`, {
      contact_method: method,
      page_language: getLocale(),
      page_path: window.location.pathname
    });
  }

  function handleInquirySuccess(event) {
    const detail = event.detail && typeof event.detail === 'object' ? event.detail : {};
    trackEvent('generate_lead', {
      form_id: detail.form_id || 'inquiry-form',
      product_interest: detail.product_interest || 'not_specified',
      page_language: detail.page_language || getLocale()
    });
  }

  function handleKeydown(event) {
    if (!dialog || dialog.hidden) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      if (!settingsPanel.hidden) {
        setPanel('main');
      } else if (activeConsent) {
        hideDialog();
      }
      return;
    }

    if (event.key !== 'Tab') return;
    const focusable = Array.from(
      dialog.querySelectorAll('a[href], button:not([disabled]), input:not([disabled])')
    ).filter((element) => !element.closest('[hidden]'));
    if (!focusable.length) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function initialize() {
    createDialog();
    createSettingsLauncher();
    injectFooterControls();
    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('alumcraft:inquiry-success', handleInquirySuccess);

    if (activeConsent) {
      applyConsent(activeConsent);
    } else {
      showDialog('main');
    }
  }

  window.AlumCraftMarketing = {
    __initialized: true,
    openSettings,
    getAttribution,
    trackEvent
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();
