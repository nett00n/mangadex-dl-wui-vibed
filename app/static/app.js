/*
 * Copyright (c) - All Rights Reserved.
 *
 * This project is licenced under the GPLv3.
 * See the LICENSE file for more information.
 */

// mangadex-dl-wui-vibed frontend JavaScript

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
     * @param {string} url - MangaDex URL for this task
     */
    addTask(taskId, url) {
        this.tasks.set(taskId, { status: 'queued', url: url });
        this.saveTasks();
        this.startPolling(taskId);
    },

    /**
     * Update task status
     * @param {string} taskId - Task ID
     * @param {Object} status - Status data from API
     */
    updateTask(taskId, status) {
        // Preserve URL from existing task data if not in status
        const existingTask = this.tasks.get(taskId);
        if (existingTask && existingTask.url && !status.url) {
            status.url = existingTask.url;
        }

        this.tasks.set(taskId, status);
        this.saveTasks();
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
        this.saveTasks();
        UI.removeTaskCard(taskId);
    },

    /**
     * Save tasks to sessionStorage
     */
    saveTasks() {
        const data = {};
        for (const [id, task] of this.tasks) {
            data[id] = task;
        }
        sessionStorage.setItem('mangadex-tasks', JSON.stringify(data));
    },

    /**
     * Load tasks from sessionStorage
     */
    loadTasks() {
        const raw = sessionStorage.getItem('mangadex-tasks');
        if (!raw) return;
        try {
            const data = JSON.parse(raw);
            for (const [id, task] of Object.entries(data)) {
                this.tasks.set(id, task);
                UI.renderTask(id, task);
                // Resume polling for non-terminal tasks
                if (task.status !== 'finished' && task.status !== 'failed') {
                    this.startPolling(id);
                } else if (task.status === 'finished' && (!task.files || task.files.length === 0)) {
                    // One-time refresh to get file list from API
                    this.refreshFinishedTask(id);
                }
            }
        } catch {
            // Corrupt data, ignore
        }
    },

    /**
     * Refresh a finished task to get file list from API
     * @param {string} taskId - Task ID
     */
    async refreshFinishedTask(taskId) {
        try {
            const status = await ApiClient.getStatus(taskId);
            if (status.status === 'finished' && status.files) {
                this.updateTask(taskId, status);
            }
        } catch {
            // API unavailable or job expired — keep sessionStorage data as-is
        }
    },
};

// UI Manager for rendering
const UI = {
    /**
     * Render or update task card
     * @param {string} taskId - Task ID
     * @param {Object} status - Status data
     *
     * SYNC: This function and app/templates/partials/_manga_card.html render
     * structurally equivalent cards. When modifying the card layout,
     * update both to keep the visual structure consistent.
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
        const mangaName = status.url ? this.extractMangaName(status.url) : null;
        let html = `
            <div class="task-header">
                <div>
                    <span class="task-id">Task ID: ${this.escapeHtml(taskId)}</span>
                    ${mangaName ? `<span class="task-url"><a href="${this.escapeHtml(status.url)}" target="_blank" rel="noopener">${this.escapeHtml(mangaName)}</a></span>` : ''}
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
                const parts = file.split('/');
                const chapterName = parts[parts.length - 1];
                const seriesName = parts.length >= 2 ? parts[parts.length - 2] : null;
                const displayName = seriesName
                    ? `${this.sanitizeFilename(seriesName)} - ${this.sanitizeFilename(chapterName)}`
                    : this.sanitizeFilename(chapterName);
                const fileUrl = ApiClient.getFileUrl(taskId, chapterName);
                html += `<li><a href="${fileUrl}" download="${this.escapeHtml(displayName)}">${this.escapeHtml(displayName)}</a></li>`;
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
     * @param {string} taskId - Failed task ID
     */
    retryTask(taskId) {
        const task = TaskManager.tasks.get(taskId);
        const url = task?.url;
        TaskManager.removeTask(taskId);
        if (url) {
            document.getElementById('manga-url').value = url;
        } else {
            this.renderError('Please re-enter the URL and submit again.');
        }
    },

    /**
     * Sanitize a filename by replacing characters unsafe on Windows/Linux/macOS
     * @param {string} name - Raw name string
     * @returns {string}
     */
    sanitizeFilename(name) {
        return name.replace(/[/<>:"\\|?*]/g, '_').replace(/_+/g, '_').replace(/^[_ .]+|[_ .]+$/g, '') || 'download';
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

    /**
     * Extract manga name from MangaDex URL
     * @param {string} url - MangaDex URL
     * @returns {string} - Manga name or URL if extraction fails
     */
    extractMangaName(url) {
        try {
            const parts = new URL(url).pathname.split('/').filter(Boolean);
            // parts = ["title", "uuid"] or ["title", "uuid", "slug"]
            const raw = parts.length >= 3 ? parts[2] : (parts[1] || url);
            return raw.replace(/-/g, ' ');
        } catch {
            return url;
        }
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
            TaskManager.addTask(result.task_id, url);
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

    // Load tasks from sessionStorage
    TaskManager.loadTasks();
});
