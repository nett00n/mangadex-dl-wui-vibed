/*
 * Copyright (c) - All Rights Reserved.
 *
 * This project is licenced under the GPLv3.
 * See the LICENSE file for more information.
 */

// mangadex-dl-wui frontend JavaScript

// API Client for backend communication
const ApiClient = {
    /**
     * Submit a download request
     * @param {string} url - MangaDex URL to download
     * @returns {Promise<{task_id: string} | {error: string}>}
     */
    async postDownload(url) {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url }),
        });
        return await response.json();
    },

    /**
     * Get task status
     * @param {string} taskId - Task ID to check
     * @returns {Promise<Object>}
     */
    async getStatus(taskId) {
        const response = await fetch(`/api/status/${taskId}`);
        return await response.json();
    },

    /**
     * Build file download URL
     * @param {string} taskId - Task ID
     * @param {string} filename - File name
     * @returns {string}
     */
    getFileUrl(taskId, filename) {
        return `/api/file/${taskId}/${filename}`;
    },
};

// Task Manager for state management and polling
const TaskManager = {
    tasks: new Map(),
    pollingIntervals: new Map(),

    /**
     * Add a new task
     * @param {string} taskId - Task ID
     */
    addTask(taskId) {
        this.tasks.set(taskId, { status: 'queued' });
        this.startPolling(taskId);
    },

    /**
     * Update task status
     * @param {string} taskId - Task ID
     * @param {Object} status - Status data from API
     */
    updateTask(taskId, status) {
        this.tasks.set(taskId, status);
        UI.renderTask(taskId, status);

        // Stop polling if task is finished or failed
        if (status.status === 'finished' || status.status === 'failed') {
            this.stopPolling(taskId);
        }
    },

    /**
     * Start polling for task status
     * @param {string} taskId - Task ID
     * @param {number} interval - Polling interval in ms (default: 2000)
     */
    startPolling(taskId, interval = 2000) {
        if (this.pollingIntervals.has(taskId)) {
            return; // Already polling
        }

        const poll = async () => {
            try {
                const status = await ApiClient.getStatus(taskId);
                // Check if response is an API error (no status field, only error)
                if (status.error && !status.status) {
                    // Task not found or API error
                    this.stopPolling(taskId);
                    UI.renderError(`Task ${taskId}: ${status.error}`);
                    return;
                }
                this.updateTask(taskId, status);
            } catch (error) {
                console.error('Polling error:', error);
                // Don't stop polling on network errors, will retry
            }
        };

        // Initial poll
        poll();

        // Set up interval
        const intervalId = setInterval(poll, interval);
        this.pollingIntervals.set(taskId, intervalId);
    },

    /**
     * Stop polling for task status
     * @param {string} taskId - Task ID
     */
    stopPolling(taskId) {
        const intervalId = this.pollingIntervals.get(taskId);
        if (intervalId) {
            clearInterval(intervalId);
            this.pollingIntervals.delete(taskId);
        }
    },

    /**
     * Remove task from manager
     * @param {string} taskId - Task ID
     */
    removeTask(taskId) {
        this.stopPolling(taskId);
        this.tasks.delete(taskId);
        UI.removeTaskCard(taskId);
    },
};

// UI Manager for rendering
const UI = {
    /**
     * Render or update task card
     * @param {string} taskId - Task ID
     * @param {Object} status - Status data
     */
    renderTask(taskId, status) {
        let card = document.getElementById(`task-${taskId}`);

        if (!card) {
            // Create new card
            card = document.createElement('div');
            card.id = `task-${taskId}`;
            card.className = 'task-card';
            document.getElementById('tasks-container').prepend(card);
        }

        // Build card HTML
        let html = `
            <div class="task-header">
                <div>
                    <span class="task-id">Task ID: ${this.escapeHtml(taskId)}</span>
                    <span class="status-badge ${status.status}">${status.status}</span>
                </div>
                <div class="task-actions">
                    ${status.status === 'failed' ? '<button class="btn-retry" onclick="UI.retryTask(\'' + taskId + '\')">Retry</button>' : ''}
                    <button class="btn-dismiss" onclick="TaskManager.removeTask('${taskId}')">Dismiss</button>
                </div>
            </div>
        `;

        // Add progress indicator for running tasks (status-only, no chapter tracking)
        if (status.status === 'started') {
            html += `
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill indeterminate">
                            Downloading...
                        </div>
                    </div>
                </div>
            `;
        }

        // Add error message for failed tasks
        if (status.status === 'failed' && status.error) {
            html += `
                <div class="error-message">
                    ${this.escapeHtml(status.error)}
                </div>
            `;
        }

        // Add file list for completed tasks
        if (status.status === 'finished' && status.files && status.files.length > 0) {
            html += '<div class="file-list"><h4>Downloaded Files:</h4><ul>';
            for (const file of status.files) {
                const filename = file.split('/').pop();
                const fileUrl = ApiClient.getFileUrl(taskId, filename);
                html += `<li><a href="${fileUrl}" download>${this.escapeHtml(filename)}</a></li>`;
            }
            html += '</ul></div>';
        }

        card.innerHTML = html;
    },

    /**
     * Display error message
     * @param {string} message - Error message
     */
    renderError(message) {
        const container = document.getElementById('error-container');
        container.textContent = message;
        container.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            container.classList.add('hidden');
        }, 5000);
    },

    /**
     * Hide error message
     */
    hideError() {
        document.getElementById('error-container').classList.add('hidden');
    },

    /**
     * Set submit button state
     * @param {boolean} disabled - Whether button should be disabled
     */
    setButtonState(disabled) {
        const button = document.getElementById('submit-button');
        button.disabled = disabled;
        button.textContent = disabled ? 'Downloading...' : 'Download';
    },

    /**
     * Remove task card from DOM
     * @param {string} taskId - Task ID
     */
    removeTaskCard(taskId) {
        const card = document.getElementById(`task-${taskId}`);
        if (card) {
            card.remove();
        }
    },

    /**
     * Retry a failed download
     * @param {string} taskId - Failed task ID (not used, starts new download)
     */
    retryTask(taskId) {
        // Get the URL from the original submission (we don't store it, so just clear form)
        // In a real app, we'd store the URL with the task
        TaskManager.removeTask(taskId);
        this.renderError('Please re-enter the URL and submit again.');
    },

    /**
     * Escape HTML to prevent XSS
     * @param {string} text - Text to escape
     * @returns {string}
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

// Form submission handler
let lastSubmitTime = 0;
const SUBMIT_DEBOUNCE_MS = 1000;

async function handleSubmit(event) {
    event.preventDefault();

    // Debounce rapid submits
    const now = Date.now();
    if (now - lastSubmitTime < SUBMIT_DEBOUNCE_MS) {
        return;
    }
    lastSubmitTime = now;

    // Hide any previous errors
    UI.hideError();

    // Get form data
    const form = event.target;
    const urlInput = form.querySelector('#manga-url');
    const url = urlInput.value.trim();

    // Client-side validation
    if (!url) {
        UI.renderError('Please enter a URL');
        return;
    }

    // Disable button during submission
    UI.setButtonState(true);

    try {
        // Submit to API
        const result = await ApiClient.postDownload(url);

        if (result.error) {
            // Server returned error
            UI.renderError(result.error);
        } else if (result.task_id) {
            // Success - add task and start polling
            TaskManager.addTask(result.task_id);
            // Clear form
            urlInput.value = '';
        } else {
            UI.renderError('Unexpected server response');
        }
    } catch (error) {
        console.error('Submit error:', error);
        UI.renderError('Network error: Could not connect to server');
    } finally {
        // Re-enable button
        UI.setButtonState(false);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('download-form');
    form.addEventListener('submit', handleSubmit);
});
