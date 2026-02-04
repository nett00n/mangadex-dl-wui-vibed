// TODO: Implement polling and form submission

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('download-form');
    const statusDiv = document.getElementById('status');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        statusDiv.textContent = 'Form submission not yet implemented';
        statusDiv.classList.add('active');
    });
});
