// ═══════════════════════════════════════════════════════════════════
// BrandProof – Alpine.js SPA Application
// ═══════════════════════════════════════════════════════════════════

function brandproof() {
    return {
        // ── State ────────────────────────────────────────────────
        user: null,
        token: null,
        page: 'landing',
        loading: false,
        toasts: [],

        // Creator
        draftTitle: '',
        draftText: '',
        samples: [],
        selectedSample: '',
        currentSubmission: null,
        findings: [],
        aiStatus: 'available',

        // Manager
        activeManagerTab: 'rules',
        rules: [],
        ledgerEntries: [],
        termsData: [],

        // Reviewer
        submissions: [],
        selectedVersion: 1,
        commentText: '',
        resubmitText: '',

        // Insights
        insightsData: {},

        // Disclosure
        disclosureData: {},

        // Modals
        showEditModal: false,
        editFinding: null,
        editText: '',
        showDisputeModal: false,
        disputeFinding: null,
        disputeReason: '',
        showOverrideModal: false,
        overrideMessage: '',
        overrideReason: '',

        // ── Init ─────────────────────────────────────────────────
        async init() {
            // Restore session from localStorage
            const saved = localStorage.getItem('bp_token');
            const savedUser = localStorage.getItem('bp_user');
            if (saved && savedUser) {
                this.token = saved;
                this.user = JSON.parse(savedUser);
                // Verify token
                try {
                    const resp = await this.api('/api/me');
                    if (resp) {
                        this.navigateToRole();
                    } else {
                        this.logout();
                    }
                } catch {
                    this.logout();
                }
            }
            // Load samples
            try {
                const data = await this.apiFetch('/api/samples');
                this.samples = data.drafts || [];
            } catch {}
        },

        // ── API helpers ──────────────────────────────────────────
        async apiFetch(url, options = {}) {
            const headers = { 'Content-Type': 'application/json', ...options.headers };
            if (this.token) headers['Authorization'] = 'Bearer ' + this.token;
            const resp = await fetch(url, { ...options, headers });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'Request failed' }));
                throw new Error(err.detail || 'Request failed');
            }
            return resp.json();
        },

        async api(url, options = {}) {
            try {
                return await this.apiFetch(url, options);
            } catch (e) {
                this.toast(e.message, 'error');
                return null;
            }
        },

        // ── Auth ─────────────────────────────────────────────────
        async login(role) {
            try {
                const data = await this.apiFetch('/api/auth/demo', {
                    method: 'POST',
                    body: JSON.stringify({ role }),
                });
                this.token = data.token;
                this.user = data.user;
                localStorage.setItem('bp_token', data.token);
                localStorage.setItem('bp_user', JSON.stringify(data.user));
                this.toast('Welcome, ' + data.user.name + '!', 'success');
                this.navigateToRole();
            } catch (e) {
                this.toast('Login failed: ' + e.message, 'error');
            }
        },

        logout() {
            this.user = null;
            this.token = null;
            this.page = 'landing';
            this.currentSubmission = null;
            this.findings = [];
            this.submissions = [];
            localStorage.removeItem('bp_token');
            localStorage.removeItem('bp_user');
        },

        navigateToRole() {
            if (!this.user) return;
            if (this.user.role === 'creator') {
                this.page = 'creator';
                this.loadSamples();
            } else if (this.user.role === 'manager') {
                this.page = 'manager';
                this.loadRules();
            } else if (this.user.role === 'reviewer') {
                this.page = 'reviewer';
                this.loadSubmissions();
            }
        },

        async loginThenDisclosure() {
            // Login as creator then show disclosure
            await this.login('creator');
            this.page = 'disclosure';
            this.loadDisclosure();
        },

        // ── Samples ──────────────────────────────────────────────
        async loadSamples() {
            try {
                const data = await this.apiFetch('/api/samples');
                this.samples = data.drafts || [];
                // Auto-load first sample for demo
                if (this.samples.length > 0 && !this.draftText) {
                    this.selectedSample = '0';
                    this.loadSample();
                }
            } catch {}
        },

        loadSample() {
            const idx = parseInt(this.selectedSample);
            if (isNaN(idx) || !this.samples[idx]) return;
            this.draftTitle = this.samples[idx].title;
            this.draftText = this.samples[idx].text;
            this.currentSubmission = null;
            this.findings = [];
        },

        // ── Submit & Review ──────────────────────────────────────
        async submitAndReview() {
            if (!this.draftText.trim()) return;
            this.loading = true;
            try {
                // Create submission
                const sub = await this.apiFetch('/api/submissions', {
                    method: 'POST',
                    body: JSON.stringify({
                        title: this.draftTitle || 'Untitled Draft',
                        text: this.draftText,
                    }),
                });

                // Run review
                const result = await this.apiFetch('/api/submissions/' + sub.id + '/review', {
                    method: 'POST',
                });

                this.aiStatus = result.ai_status || 'available';
                this.findings = result.findings || [];

                // Load full submission
                await this.loadSubmission(sub.id);

                this.toast('Review complete: ' + this.findings.length + ' finding(s)', 'info');
            } catch (e) {
                this.toast('Review failed: ' + e.message, 'error');
            }
            this.loading = false;
        },

        async uploadFile(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.loading = true;
            try {
                const formData = new FormData();
                formData.append('title', file.name.replace(/\.\w+$/, ''));
                formData.append('file', file);

                const headers = {};
                if (this.token) headers['Authorization'] = 'Bearer ' + this.token;

                const resp = await fetch('/api/submissions/upload', {
                    method: 'POST',
                    headers,
                    body: formData,
                });
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    throw new Error(err.detail || 'Upload failed');
                }
                const sub = await resp.json();

                // Run review
                const result = await this.apiFetch('/api/submissions/' + sub.id + '/review', {
                    method: 'POST',
                });

                this.aiStatus = result.ai_status || 'available';
                this.findings = result.findings || [];
                await this.loadSubmission(sub.id);
                this.toast('File uploaded and reviewed!', 'success');
            } catch (e) {
                this.toast('Upload failed: ' + e.message, 'error');
            }
            this.loading = false;
            event.target.value = '';
        },

        // ── Load data ────────────────────────────────────────────
        async loadSubmission(id) {
            const data = await this.api('/api/submissions/' + id);
            if (data) {
                this.currentSubmission = data;
                this.findings = data.findings || [];
                this.selectedVersion = data.current_version;
                // Set resubmit text from latest version
                const latest = (data.versions || []).find(v => v.version_no === data.current_version);
                if (latest) this.resubmitText = latest.text;
            }
        },

        async loadSubmissions() {
            const data = await this.api('/api/submissions');
            if (data) this.submissions = data;
        },

        async loadRules() {
            const data = await this.api('/api/rules');
            if (data) this.rules = data;
        },

        async loadLedger() {
            const data = await this.api('/api/ledger');
            if (data) this.ledgerEntries = data;
        },

        async loadTerms() {
            const data = await this.api('/api/terms');
            if (data) this.termsData = data;
        },

        async loadInsights() {
            const data = await this.api('/api/insights');
            if (data) this.insightsData = data;
        },

        async loadDisclosure() {
            const data = await this.api('/api/disclosure');
            if (data) this.disclosureData = data;
        },

        // ── Open submission detail ───────────────────────────────
        async openSubmission(id) {
            await this.loadSubmission(id);
            this.page = 'submission-detail';
        },

        goBack() {
            if (this.user.role === 'creator') {
                this.page = 'my-submissions';
                this.loadSubmissions();
            } else {
                this.page = 'reviewer';
                this.loadSubmissions();
            }
        },

        // ── Finding decisions ────────────────────────────────────
        async decideFinding(findingId, decision, editedText, disputeReason) {
            const body = { decision };
            if (editedText) body.edited_text = editedText;
            if (disputeReason) body.dispute_reason = disputeReason;

            const result = await this.api('/api/findings/' + findingId + '/decision', {
                method: 'POST',
                body: JSON.stringify(body),
            });

            if (result) {
                // Update local state
                const f = this.findings.find(f => f.id === findingId);
                if (f) {
                    f.decision = decision;
                    if (editedText) f.edited_text = editedText;
                    if (disputeReason) f.dispute_reason = disputeReason;
                }
                this.toast('Decision recorded: ' + decision, 'success');
            }
        },

        startEdit(finding) {
            this.editFinding = finding;
            this.editText = finding.suggestion || finding.flagged_text || '';
            this.showEditModal = true;
        },

        async submitEdit() {
            if (!this.editFinding || !this.editText.trim()) return;
            await this.decideFinding(this.editFinding.id, 'edited', this.editText);
            this.showEditModal = false;
        },

        startDispute(finding) {
            this.disputeFinding = finding;
            this.disputeReason = '';
            this.showDisputeModal = true;
        },

        async submitDispute() {
            if (!this.disputeFinding || !this.disputeReason.trim()) return;
            await this.decideFinding(this.disputeFinding.id, 'disputed', null, this.disputeReason);
            this.showDisputeModal = false;
        },

        // ── Apply accepted changes ───────────────────────────────
        applyAccepted() {
            if (!this.currentSubmission || !this.currentSubmission.versions) return;
            const latest = this.currentSubmission.versions.find(
                v => v.version_no === this.currentSubmission.current_version
            );
            if (!latest) return;

            let text = latest.text;
            // Sort findings by span_start descending to replace from end
            const accepted = this.findings
                .filter(f => f.decision === 'accepted' || f.decision === 'edited')
                .filter(f => f.span_start != null && f.span_end != null)
                .sort((a, b) => b.span_start - a.span_start);

            for (const f of accepted) {
                let replacement = '';
                if (f.decision === 'edited' && f.edited_text) {
                    replacement = f.edited_text;
                } else if (f.suggestion) {
                    // Extract replacement from suggestion if possible
                    replacement = ''; // Remove the flagged text for accepted
                }

                if (f.span_start >= 0 && f.span_end <= text.length) {
                    text = text.substring(0, f.span_start) + replacement + text.substring(f.span_end);
                }
            }

            this.resubmitText = text.trim();
            this.toast('Accepted changes applied to resubmit text. Review and submit!', 'info');

            // If in creator view, auto-fill draft
            if (this.page === 'creator') {
                this.draftText = this.resubmitText;
            }
        },

        // ── Submit for review ────────────────────────────────────
        submitForReview() {
            this.toast('Submission is in review. Switch to Reviewer role to approve.', 'info');
        },

        // ── Resubmit ─────────────────────────────────────────────
        async resubmit() {
            if (!this.currentSubmission || !this.resubmitText.trim()) return;
            this.loading = true;
            try {
                const result = await this.apiFetch(
                    '/api/submissions/' + this.currentSubmission.id + '/resubmit',
                    { method: 'POST', body: JSON.stringify({ text: this.resubmitText }) }
                );
                this.toast('Resubmitted as version ' + result.version_no + ' with ' + result.findings_count + ' findings', 'success');
                await this.loadSubmission(this.currentSubmission.id);
            } catch (e) {
                this.toast('Resubmit failed: ' + e.message, 'error');
            }
            this.loading = false;
        },

        // ── Comments ─────────────────────────────────────────────
        async addComment() {
            if (!this.currentSubmission || !this.commentText.trim()) return;
            const result = await this.api(
                '/api/submissions/' + this.currentSubmission.id + '/comments',
                { method: 'POST', body: JSON.stringify({ body: this.commentText }) }
            );
            if (result) {
                if (!this.currentSubmission.comments) this.currentSubmission.comments = [];
                this.currentSubmission.comments.push(result);
                this.commentText = '';
                this.toast('Comment added', 'success');
            }
        },

        // ── Approve / Request Changes ────────────────────────────
        async approveSubmission() {
            if (!this.currentSubmission) return;
            try {
                const result = await this.apiFetch(
                    '/api/submissions/' + this.currentSubmission.id + '/approve',
                    { method: 'POST', body: JSON.stringify({}) }
                );
                this.currentSubmission.status = 'approved';
                this.toast('Submission approved! ✅', 'success');
            } catch (e) {
                // Check if it's pending findings error
                if (e.message && e.message.includes('pending')) {
                    this.overrideMessage = e.message;
                    this.overrideReason = '';
                    this.showOverrideModal = true;
                } else {
                    this.toast(e.message, 'error');
                }
            }
        },

        async submitOverride() {
            if (!this.currentSubmission || !this.overrideReason.trim()) return;
            try {
                await this.apiFetch(
                    '/api/submissions/' + this.currentSubmission.id + '/approve',
                    { method: 'POST', body: JSON.stringify({ override_reason: this.overrideReason }) }
                );
                this.currentSubmission.status = 'approved';
                this.showOverrideModal = false;
                this.toast('Submission approved with override ✅', 'success');
            } catch (e) {
                this.toast(e.message, 'error');
            }
        },

        async requestChanges() {
            if (!this.currentSubmission) return;
            const reason = prompt('Reason for requesting changes (optional):') || '';
            const body = reason ? { body: reason } : { body: 'Changes requested by reviewer' };
            const result = await this.api(
                '/api/submissions/' + this.currentSubmission.id + '/request-changes',
                { method: 'POST', body: JSON.stringify(body) }
            );
            if (result) {
                this.currentSubmission.status = 'changes_requested';
                this.toast('Changes requested', 'info');
                await this.loadSubmission(this.currentSubmission.id);
            }
        },

        // ── Highlighted text ─────────────────────────────────────
        highlightedText() {
            if (!this.currentSubmission || !this.currentSubmission.versions) return '';
            const version = this.currentSubmission.versions.find(
                v => v.version_no === this.selectedVersion
            );
            if (!version) return '';

            const text = version.text;
            const versionFindings = this.findings.filter(
                f => f.version_id === version.id && f.span_start != null && f.span_end != null
            );

            if (versionFindings.length === 0) return this.escapeHtml(text);

            // Sort by span_start
            const sorted = [...versionFindings].sort((a, b) => a.span_start - b.span_start);

            let result = '';
            let lastIdx = 0;

            for (const f of sorted) {
                if (f.span_start < lastIdx) continue; // overlapping
                if (f.span_start > lastIdx) {
                    result += this.escapeHtml(text.substring(lastIdx, f.span_start));
                }
                const spanClass = 'highlight-' + f.severity;
                const title = f.category + ': ' + f.verdict;
                result += '<span class="highlight-span ' + spanClass + '" title="' + this.escapeHtml(title) + '">';
                result += this.escapeHtml(text.substring(f.span_start, f.span_end));
                result += '</span>';
                lastIdx = f.span_end;
            }

            if (lastIdx < text.length) {
                result += this.escapeHtml(text.substring(lastIdx));
            }

            return result;
        },

        escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        },

        // ── Toast ────────────────────────────────────────────────
        toast(msg, type = 'info') {
            const t = { msg, type, visible: true };
            this.toasts.push(t);
            setTimeout(() => {
                t.visible = false;
                setTimeout(() => {
                    const idx = this.toasts.indexOf(t);
                    if (idx > -1) this.toasts.splice(idx, 1);
                }, 500);
            }, 3500);
        },
    };
}
