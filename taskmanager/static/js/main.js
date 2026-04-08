function openModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add('open');
    const first = el.querySelector('input[type="text"], input[type="email"], textarea');
    if (first) setTimeout(() => first.focus(), 50);
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});

// Close modal on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

// Auto-hide flash messages
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(f => {
    f.style.transition = 'opacity 0.4s';
    f.style.opacity = '0';
    setTimeout(() => f.remove(), 400);
  });
}, 3500);

// Poll unread messages count for nav badge
async function pollUnread() {
  try {
    const res  = await fetch('/chat/unread');
    const data = await res.json();
    const badge = document.getElementById('totalUnread');
    if (badge) {
      if (data.count > 0) {
        badge.textContent = data.count;
        badge.style.display = 'inline-flex';
      } else {
        badge.style.display = 'none';
      }
    }
  } catch(e) {}
}
pollUnread();
setInterval(pollUnread, 5000);

