// staff_app/static/staff_app/js/profile.js
// ADDED: simple script to enable Save button only when user makes a change
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('profileForm');
  const saveBtn = document.getElementById('saveBtn');
  if (!form || !saveBtn) return;

  // Mark save button disabled initially
  saveBtn.disabled = true;

  // When any input changes, enable save button
  const inputs = form.querySelectorAll('input, textarea, select');
  inputs.forEach(input => {
    // For file input, listen to change
    if (input.type === 'file') {
      input.addEventListener('change', () => {
        saveBtn.disabled = false;
        // preview image if possible
        const file = input.files[0];
        if (file) {
          const preview = document.getElementById('previewImage');
          if (preview) {
            const reader = new FileReader();
            reader.onload = function (e) {
              preview.src = e.target.result;
            };
            reader.readAsDataURL(file);
          }
        }
      });
    } else {
      input.addEventListener('input', () => {
        saveBtn.disabled = false;
      });
      // also listen for blur and change
      input.addEventListener('change', () => {
        saveBtn.disabled = false;
      });
    }
  });

  // Optional: prevent accidental navigate away if unsaved changes (simple prompt)
  let formDirty = false;
  inputs.forEach(i => {
    i.addEventListener('input', () => { formDirty = true; });
    i.addEventListener('change', () => { formDirty = true; });
  });

  window.addEventListener('beforeunload', function (e) {
    if (formDirty && !saveBtn.disabled) {
      const confirmationMessage = 'You have unsaved changes. Are you sure you want to leave?';
      e.returnValue = confirmationMessage;
      return confirmationMessage;
    }
  });

  // When form submitted, allow navigation
  form.addEventListener('submit', () => {
    formDirty = false;
  });
});
