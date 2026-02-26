document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const fileInput = document.getElementById('file-input');
    const uploadContainer = document.getElementById('upload-container');
    const processingContainer = document.getElementById('processing-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const billPopup = document.getElementById('bill-popup');
    const billPopupContent = document.getElementById('bill-popup-content');
    const closePopupBtn = document.getElementById('close-popup');
    const popupActionBtn = document.getElementById('popup-action-btn');
    const distortionControls = document.getElementById('distortion-controls');
    const toggleControlsBtn = document.getElementById('toggle-controls');
    const controlsContent = document.getElementById('controls-content');
    const cipherTriangleBtn = document.getElementById('cipher-triangle-btn');
    const resultContainer = document.getElementById('result-container');
    const resultVideo = document.getElementById('result-video');
    const downloadBtn = document.getElementById('download-btn');
    const resetBtn = document.getElementById('reset-btn');
    const captionOverlay = document.getElementById('caption-overlay');
    const promptSearch = document.getElementById('prompt-search');
    const manualPrompt = document.getElementById('manual-prompt');
    const manualTranscript = document.getElementById('manual-transcript');
    const rerunPromptBtn = document.getElementById('rerun-prompt-btn');
    const rerunTranscriptBtn = document.getElementById('rerun-transcript-btn');
    const loadTranscriptBtn = document.getElementById('load-transcript-btn');
    const revertBtn = document.getElementById('revert-btn');
    const rerunSpinner = document.getElementById('rerun-spinner');
    const rerunStatus = document.getElementById('rerun-status');
    const manualCuts = document.getElementById('manual-cuts');
    const rerunCutsBtn = document.getElementById('rerun-cuts-btn');
    const errorText = document.getElementById('error-text');

    // --- State ---
    let selectedStyle = 'sleek';
    let captionsData = null;
    let currentVideoId = null;
    let lastTranscript = '';
    let lastPrompt = 'Make this video engaging for social media';
    let selectedMusicFile = null;
    let wavesurfer = null; // Store WaveSurfer instance

    // --- Platform, Format & Advanced Options State ---
    let selectedPlatform = 'tiktok';
    let selectedFormat = 'short';
    let selectedAspect = '9:16';
    let selectedRes = '1080x1920';
    let rotationDeg = 0;
    let flipHorizontal = false;
    let customAspect = null; // { w, h } or null
    let selectedCropPreset = null;
    const styleButtonClasses = {
        active: ['active', 'border-[#F4E04D]', 'bg-[#F4E04D]/10', 'text-[#F4E04D]'],
        inactive: ['border-[#333]', 'text-gray-400']
    };

    // Music elements
    const addMusicToggle = document.getElementById('add-music-toggle');
    const musicOptions = document.getElementById('music-options');
    const musicSelect = document.getElementById('music-select');
    const selectedMusicName = document.getElementById('selected-music-name');
    const musicUpload = document.getElementById('music-upload');
    const musicVolume = document.getElementById('music-volume');
    const volumeDisplay = document.getElementById('volume-display');

    // --- Initialization ---
    lucide.createIcons();
    initGlitchEffect();
    initBillBackground();
    initWaveSurfer(); // Initialize visualization
    initProgressWebSocket(); // Real-time progress connection

    // Show controls on load
    setTimeout(() => {
        if (distortionControls) distortionControls.classList.remove('opacity-0');
    }, 500);

    // === Platform + Format Selection ===
    const platformBtnClasses = {
        active: ['active', 'border-[#F4E04D]', 'bg-[#F4E04D]/10', 'text-[#F4E04D]'],
        inactive: ['border-[#333]', 'bg-[#0a0a0a]', 'text-gray-400']
    };

    document.querySelectorAll('.platform-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.platform-btn').forEach(b => {
                b.classList.remove(...platformBtnClasses.active);
                b.classList.add(...platformBtnClasses.inactive);
            });
            btn.classList.remove(...platformBtnClasses.inactive);
            btn.classList.add(...platformBtnClasses.active);
            selectedPlatform = btn.dataset.platform;
            selectedAspect = btn.dataset.aspect;
            selectedRes = btn.dataset.res;
        });
    });

    document.querySelectorAll('.format-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.format-btn').forEach(b => {
                b.classList.remove('active', 'bg-[#F4E04D]', 'text-black');
                b.classList.add('bg-[#0a0a0a]', 'text-gray-400');
            });
            btn.classList.remove('bg-[#0a0a0a]', 'text-gray-400');
            btn.classList.add('active', 'bg-[#F4E04D]', 'text-black');
            selectedFormat = btn.dataset.format;
            const hint = document.getElementById('format-hint');
            if (hint) {
                hint.textContent = selectedFormat === 'short' ? 'Optimized for \u226460s clips' : 'Full-length video export';
            }
        });
    });

    // === Advanced Options Toolbar ===
    const toggleAdvancedBtn = document.getElementById('toggle-advanced');
    const advancedContent = document.getElementById('advanced-content');
    const advancedChevron = document.getElementById('advanced-chevron');

    if (toggleAdvancedBtn && advancedContent) {
        toggleAdvancedBtn.addEventListener('click', () => {
            advancedContent.classList.toggle('hidden');
            if (advancedChevron) {
                advancedChevron.style.transform = advancedContent.classList.contains('hidden') ? 'rotate(0deg)' : 'rotate(180deg)';
            }
            // Re-create Lucide icons for newly-visible content
            lucide.createIcons();
        });
    }

    // Rotate Button
    const btnRotate = document.getElementById('btn-rotate');
    const rotationIndicator = document.getElementById('rotation-indicator');
    if (btnRotate) {
        btnRotate.addEventListener('click', () => {
            rotationDeg = (rotationDeg + 90) % 360;
            if (rotationDeg === 0) {
                rotationIndicator?.classList.add('hidden');
                btnRotate.classList.remove('border-[#F4E04D]', 'text-[#F4E04D]', 'bg-[#F4E04D]/10');
                btnRotate.classList.add('border-[#333]', 'text-gray-400', 'bg-[#111]');
            } else {
                if (rotationIndicator) {
                    rotationIndicator.classList.remove('hidden');
                    rotationIndicator.textContent = rotationDeg + '\u00b0';
                }
                btnRotate.classList.remove('border-[#333]', 'text-gray-400', 'bg-[#111]');
                btnRotate.classList.add('border-[#F4E04D]', 'text-[#F4E04D]', 'bg-[#F4E04D]/10');
            }
        });
    }

    // Flip Button
    const btnFlip = document.getElementById('btn-flip');
    const flipIndicator = document.getElementById('flip-indicator');
    if (btnFlip) {
        btnFlip.addEventListener('click', () => {
            flipHorizontal = !flipHorizontal;
            if (flipHorizontal) {
                flipIndicator?.classList.remove('hidden');
                btnFlip.classList.remove('border-[#333]', 'text-gray-400', 'bg-[#111]');
                btnFlip.classList.add('border-[#F4E04D]', 'text-[#F4E04D]', 'bg-[#F4E04D]/10');
            } else {
                flipIndicator?.classList.add('hidden');
                btnFlip.classList.remove('border-[#F4E04D]', 'text-[#F4E04D]', 'bg-[#F4E04D]/10');
                btnFlip.classList.add('border-[#333]', 'text-gray-400', 'bg-[#111]');
            }
        });
    }

    // Crop Button — toggles presets panel
    const btnCrop = document.getElementById('btn-crop');
    const cropPresets = document.getElementById('crop-presets');
    if (btnCrop && cropPresets) {
        btnCrop.addEventListener('click', () => {
            cropPresets.classList.toggle('hidden');
            // Hide custom aspect if open
            document.getElementById('custom-aspect-input')?.classList.add('hidden');
        });
    }

    // Crop preset buttons
    document.querySelectorAll('.crop-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.crop-preset-btn').forEach(b => {
                b.classList.remove('border-[#F4E04D]', 'bg-[#F4E04D]/10', 'text-[#F4E04D]');
                b.classList.add('border-[#333]', 'text-gray-400');
            });
            btn.classList.remove('border-[#333]', 'text-gray-400');
            btn.classList.add('border-[#F4E04D]', 'bg-[#F4E04D]/10', 'text-[#F4E04D]');
            selectedCropPreset = btn.dataset.crop;
            if (selectedCropPreset === 'auto') {
                selectedCropPreset = selectedAspect; // Use platform default
            }
        });
    });

    // Custom Aspect Button — toggles input panel
    const btnCustomAspect = document.getElementById('btn-custom-aspect');
    const customAspectInput = document.getElementById('custom-aspect-input');
    if (btnCustomAspect && customAspectInput) {
        btnCustomAspect.addEventListener('click', () => {
            customAspectInput.classList.toggle('hidden');
            // Hide crop presets if open
            cropPresets?.classList.add('hidden');
        });
    }

    // Apply custom aspect
    const applyAspectBtn = document.getElementById('apply-aspect');
    if (applyAspectBtn) {
        applyAspectBtn.addEventListener('click', () => {
            const w = parseInt(document.getElementById('aspect-w')?.value || '9');
            const h = parseInt(document.getElementById('aspect-h')?.value || '16');
            if (w > 0 && h > 0) {
                customAspect = { w, h };
                btnCustomAspect?.classList.remove('border-[#333]', 'text-gray-400', 'bg-[#111]');
                btnCustomAspect?.classList.add('border-[#F4E04D]', 'text-[#F4E04D]', 'bg-[#F4E04D]/10');
            }
        });
    }

    // Reset custom aspect
    const resetAspectBtn = document.getElementById('reset-aspect');
    if (resetAspectBtn) {
        resetAspectBtn.addEventListener('click', () => {
            customAspect = null;
            const wInput = document.getElementById('aspect-w');
            const hInput = document.getElementById('aspect-h');
            if (wInput) wInput.value = '9';
            if (hInput) hInput.value = '16';
            btnCustomAspect?.classList.remove('border-[#F4E04D]', 'text-[#F4E04D]', 'bg-[#F4E04D]/10');
            btnCustomAspect?.classList.add('border-[#333]', 'text-gray-400', 'bg-[#111]');
        });
    }

    // --- Event Listeners ---

    // Toggle Controls
    if (toggleControlsBtn) {
        toggleControlsBtn.addEventListener('click', () => {
            controlsContent.classList.toggle('hidden');
            const icon = toggleControlsBtn.querySelector('i');
            if (controlsContent.classList.contains('hidden')) {
                icon.style.transform = 'rotate(0deg)';
            } else {
                icon.style.transform = 'rotate(180deg)';
            }
        });
    }

    // Style Selection
    document.querySelectorAll('.style-btn').forEach(btn => {
        btn.addEventListener('click', () => setActiveStyleButton(btn.dataset.style));
    });

    // Triangle Popup Trigger
    if (cipherTriangleBtn) {
        cipherTriangleBtn.addEventListener('click', () => {
            showPopup(false);
        });
    }

    // Close Popup
    if (closePopupBtn) closePopupBtn.addEventListener('click', closePopup);
    if (popupActionBtn) popupActionBtn.addEventListener('click', closePopup);

    // Reset
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            location.reload();
        });
    }

    // === Music Controls ===
    console.log('Music elements check:', {
        toggle: !!addMusicToggle,
        options: !!musicOptions,
        select: !!musicSelect
    });

    // Toggle music options visibility
    if (addMusicToggle) {
        addMusicToggle.addEventListener('change', () => {
            console.log('Music toggle clicked, checked:', addMusicToggle.checked);
            if (musicOptions) {
                if (addMusicToggle.checked) {
                    musicOptions.classList.remove('hidden');
                    loadAvailableMusic();
                } else {
                    musicOptions.classList.add('hidden');
                }
            }
        });
    } else {
        console.warn('addMusicToggle element not found!');
    }

    // Volume slider
    if (musicVolume && volumeDisplay) {
        musicVolume.addEventListener('input', () => {
            volumeDisplay.textContent = musicVolume.value + '%';
        });
    }

    // Music select
    if (musicSelect) {
        musicSelect.addEventListener('change', async () => {
            selectedMusicFile = musicSelect.value || null;
            if (selectedMusicFile && wavesurfer) {
                // For MVP, we presume the music file is served statically or via simple endpoint
                // We'll use a hack to load it: we need a URL. 
                // Let's assume there's a serve endpoint or we just synthesize a path if it's local.
                // Actually, let's look at list_music result. It returns 'filename'. 
                // We probably need a /api/music/stream/{filename} endpoint. 
                // For now, let's use a placeholder or just try to load from a known path if possible?
                // Real implementation: We need a getter.
                // Let's just mock the load for visual feedback or try to load if we had a URL.
                console.log("Loading waveform for", selectedMusicFile);
                // wavesurfer.load('/api/music/file/' + selectedMusicFile); // Pending endpoint
            }
        });
    }

    const previewEditBtn = document.getElementById('preview-audio-edit-btn');
    if (previewEditBtn) {
        previewEditBtn.addEventListener('click', async () => {
            if (!currentVideoId || !selectedMusicFile) {
                alert("Please upload a video and select music first.");
                return;
            }

            const btnText = previewEditBtn.innerText;
            previewEditBtn.innerText = "⏳ GENERATING...";
            previewEditBtn.disabled = true;

            try {
                const res = await fetch('/api/edit/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_id: currentVideoId,
                        audio_track_id: selectedMusicFile,
                        volume_level: (parseInt(musicVolume?.value || 30) / 100)
                    })
                });
                const data = await res.json();

                if (data.success && data.output_path) {
                    // Quick Hack: Open directly or use a simple modal
                    // We'll use the Result container temporarily
                    const videoUrl = `/api/download/${data.output_path.split('/').pop()}`;
                    window.open(videoUrl, '_blank', 'width=480,height=854');
                } else {
                    alert('Preview failed: ' + (data.error || 'Unknown'));
                }
            } catch (e) {
                console.error(e);
                alert('Preview error');
            } finally {
                previewEditBtn.innerText = btnText;
                previewEditBtn.disabled = false;
            }
        });
    }

    // Music upload
    if (musicUpload) {
        musicUpload.addEventListener('change', async (e) => {
            if (e.target.files && e.target.files[0]) {
                const file = e.target.files[0];
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const res = await fetch('/api/music/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        await loadAvailableMusic();
                        musicSelect.value = file.name;
                        selectedMusicFile = file.name;
                        if (selectedMusicName) selectedMusicName.innerText = file.name;
                        alert('Music uploaded successfully!');
                    }
                } catch (err) {
                    console.error('Music upload failed:', err);
                }
            }
        });
    }

    async function loadAvailableMusic() {
        try {
            const res = await fetch('/api/music');
            const data = await res.json();
            if (data.success && musicSelect) {
                musicSelect.innerHTML = '<option value="">-- No music selected --</option>';
                data.music.forEach(m => {
                    const opt = document.createElement('option');
                    opt.value = m.filename;
                    opt.textContent = m.name;
                    musicSelect.appendChild(opt);
                });
            }
        } catch (err) {
            console.error('Failed to load music:', err);
        }
    }


    // File Upload
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            if (e.target.files && e.target.files[0]) {
                const file = e.target.files[0];

                // Quick backend reachability check before we hide UI
                const healthy = await pingBackend();
                if (!healthy) {
                    if (errorText) {
                        errorText.classList.remove('hidden');
                        errorText.innerText = 'Error: backend is not reachable (check server on port 8000).';
                    }
                    return;
                }

                // Hide upload, show processing
                uploadContainer.classList.add('hidden');
                distortionControls.classList.add('hidden');
                const platformSelector = document.getElementById('platform-format-selector');
                if (platformSelector) platformSelector.classList.add('hidden');
                processingContainer.classList.remove('hidden');
                if (errorText) {
                    errorText.classList.add('hidden');
                    errorText.innerText = '';
                }

                try {
                    // 1. Upload
                    const formData = new FormData();
                    formData.append('file', file);
                    const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
                    const uploadData = await uploadRes.json();

                    if (!uploadData.success) throw new Error(uploadData.message);

                    const videoId = uploadData.video_id;
                    currentVideoId = videoId;
                    updateProgress(20, 'UPLOADING REALITY...');

                    // 2. Process
                    const trimBoring = document.getElementById('trim-toggle').checked;
                    const burnSubs = document.getElementById('burn-subs-toggle').checked;
                    const promptText = (promptSearch?.value || '').trim();
                    lastPrompt = promptText || lastPrompt;

                    const processRes = await fetch('/api/process', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            video_id: videoId,
                            style_preset: selectedStyle,
                            add_subtitles: burnSubs,
                            trim_boring_parts: trimBoring,
                            user_prompt: promptText || undefined,
                            platform: selectedPlatform,
                            format: selectedFormat,
                            aspect_ratio: selectedAspect,
                            resolution: selectedRes
                        })
                    });

                    const processData = await processRes.json();
                    if (!processData.success) throw new Error(processData.message);

                    // 3. Poll Status
                    pollStatus(videoId);

                } catch (err) {
                    console.error(err);
                    if (errorText) {
                        errorText.classList.remove('hidden');
                        errorText.innerText = `Error: ${err.message}`;
                    } else {
                        alert('CHAOS ERROR: ' + err.message);
                        location.reload();
                    }
                }
            }
        });
    }

    // Manual rerun with prompt
    if (rerunPromptBtn) {
        rerunPromptBtn.addEventListener('click', async () => {
            if (!currentVideoId) return;
            const promptText = (manualPrompt?.value || promptSearch?.value || '').trim();
            await reprocessWithParams({ user_prompt: promptText });
        });
    }

    // Manual rerun with transcript
    if (rerunTranscriptBtn) {
        rerunTranscriptBtn.addEventListener('click', async () => {
            if (!currentVideoId) return;
            const transcriptText = (manualTranscript?.value || '').trim();
            if (!transcriptText) {
                if (errorText) {
                    errorText.classList.remove('hidden');
                    errorText.innerText = 'Provide an edited transcript before re-running.';
                }
                return;
            }
            await reprocessWithParams({ manual_transcript: transcriptText });
        });
    }

    if (loadTranscriptBtn) {
        loadTranscriptBtn.addEventListener('click', () => {
            if (manualTranscript && lastTranscript) {
                manualTranscript.value = lastTranscript;
            }
        });
    }

    if (revertBtn) {
        revertBtn.addEventListener('click', () => {
            const defaultPrompt = 'Make this video engaging for social media';
            if (promptSearch) promptSearch.value = defaultPrompt;
            if (manualPrompt) manualPrompt.value = defaultPrompt;
            if (manualTranscript) manualTranscript.value = '';
            if (manualCuts) manualCuts.value = '';
            lastPrompt = defaultPrompt;
        });
    }

    // Manual cuts re-run
    if (rerunCutsBtn) {
        rerunCutsBtn.addEventListener('click', async () => {
            if (!currentVideoId) return;
            const segments = parseCuts(manualCuts?.value || '');
            if (!segments.length) {
                if (errorText) {
                    errorText.classList.remove('hidden');
                    errorText.innerText = 'Add at least one cut (format: start-end per line).';
                }
                return;
            }
            await reprocessWithParams(
                {
                    custom_segments: segments,
                    trim_boring_parts: false
                },
                { keepPrompt: true }
            );
        });
    }

    // Video Time Update for Subtitles
    if (resultVideo) {
        resultVideo.addEventListener('timeupdate', () => {
            if (captionsData) {
                renderCaptions(resultVideo.currentTime);
            }
        });
    }


    // --- Functions ---

    function updateProgress(percent, text) {
        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressText && text) progressText.innerText = text;
    }

    // --- Review UI Elements ---
    const reviewContainer = document.getElementById('review-container');
    const reviewSummary = document.getElementById('review-summary');
    const reviewCuts = document.getElementById('review-cuts');
    const reviewTranscript = document.getElementById('review-transcript');
    const confirmRenderBtn = document.getElementById('confirm-render-btn');

    // Review Style Selection
    document.querySelectorAll('.review-style-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            selectedStyle = (btn.dataset.style || 'sleek').toLowerCase();
            document.querySelectorAll('.review-style-btn').forEach(b => {
                b.classList.remove(...styleButtonClasses.active);
                b.classList.add(...styleButtonClasses.inactive);
                if (b.dataset.style === selectedStyle) {
                    b.classList.add(...styleButtonClasses.active);
                    b.classList.remove(...styleButtonClasses.inactive);
                }
            });
        });
    });

    if (confirmRenderBtn) {
        confirmRenderBtn.addEventListener('click', async () => {
            if (!currentVideoId) return;

            // Gather cuts
            const cuts = [];
            document.querySelectorAll('.cut-checkbox:checked').forEach(cb => {
                cuts.push({
                    start: parseFloat(cb.dataset.start),
                    end: parseFloat(cb.dataset.end)
                });
            });

            // Gather params
            const transcript = reviewTranscript.value;
            const burnSubs = document.getElementById('burn-subs-toggle').checked;

            // UI Update
            reviewContainer.classList.add('hidden');
            processingContainer.classList.remove('hidden');
            updateProgress(50, 'RENDERING REALITY...');

            try {
                const res = await fetch('/api/render', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_id: currentVideoId,
                        custom_segments: cuts.length > 0 ? cuts : null,
                        manual_transcript: transcript,
                        style_preset: selectedStyle,
                        add_subtitles: burnSubs,
                        add_music: addMusicToggle ? addMusicToggle.checked : false,
                        music_file: selectedMusicFile,
                        music_volume: musicVolume ? parseInt(musicVolume.value) / 100 : 0.3
                    })
                });

                if (!res.ok) {
                    throw new Error(`Render failed: ${res.status}`);
                }

                // Start polling for completion
                pollStatus(currentVideoId);

            } catch (e) {
                console.error(e);
                showError('Render failed: ' + e.message);
            }
        });
    }

    async function pollStatus(videoId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${videoId}`);
                if (!res.ok) {
                    clearInterval(interval);
                    showError(`Processing failed: server returned ${res.status}`);
                    return;
                }
                const data = await res.json();

                if (data.status === 'analyzed') {
                    clearInterval(interval);
                    updateProgress(50, 'ANALYSIS COMPLETE');
                    processingContainer.classList.add('hidden');
                    reviewContainer.classList.remove('hidden');
                    populateReviewUI(videoId);
                } else if (data.status === 'completed') {
                    clearInterval(interval);
                    updateProgress(100, 'REALITY ALTERED');
                    handleCompletion(data);
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    showError(`Processing failed: ${data.error || 'Unknown error'}`);
                } else {
                    const p = (data.progress || 0);
                    const stageLabel = (data.status || 'processing').toString().replace(/_/g, ' ').toUpperCase();
                    updateProgress(p, `${stageLabel}...`);
                }
            } catch (e) {
                console.error(e);
                clearInterval(interval);
                showError(`Status check failed: ${e.message}`);
            }
        }, 1000);
    }

    async function populateReviewUI(videoId) {
        // Update platform badge in review screen
        const platformLabel = document.getElementById('review-platform-label');
        const aspectLabel = document.getElementById('review-aspect-label');
        const formatLabel = document.getElementById('review-format-label');
        if (platformLabel) platformLabel.textContent = selectedPlatform.toUpperCase().replace('-', ' ');
        if (aspectLabel) aspectLabel.textContent = customAspect ? `${customAspect.w}:${customAspect.h}` : selectedAspect;
        if (formatLabel) formatLabel.textContent = selectedFormat.toUpperCase();

        // Re-create Lucide icons for new elements in review container
        lucide.createIcons();

        try {
            const res = await fetch(`/api/analysis/${videoId}`);
            const data = await res.json();

            // Overall Score with color
            const overallScore = data.ai_analysis.overall_score || 5;
            const scoreColor = overallScore >= 7 ? '#22c55e' : overallScore >= 5 ? '#eab308' : '#ef4444';

            // Summary with score
            reviewSummary.innerHTML = `
                <div class="flex items-center gap-3 mb-2">
                    <span class="text-2xl font-bold" style="color: ${scoreColor}">${overallScore}/10</span>
                    <span class="text-gray-400 text-sm">Viewer Retention Score</span>
                </div>
                <p class="text-gray-300">${data.ai_analysis.summary || "No summary available."}</p>
            `;

            // Transcript
            reviewTranscript.value = data.transcript || "";
            lastTranscript = data.transcript || "";

            // Segments with retention scores
            reviewCuts.innerHTML = '';
            const segments = data.ai_analysis.suggested_cuts || [];

            if (segments.length === 0) {
                reviewCuts.innerHTML = '<p class="text-green-500 text-sm">✅ Video looks great! No boring segments detected.</p>';
            } else {
                // Header
                const header = document.createElement('p');
                header.className = 'text-xs text-gray-500 mb-2';
                header.innerText = 'Check segments you want to REMOVE:';
                reviewCuts.appendChild(header);

                segments.forEach((seg, idx) => {
                    const score = seg.retention_score || 5;
                    const scoreColor = score >= 7 ? '#22c55e' : score >= 5 ? '#eab308' : '#ef4444';
                    const recommendation = seg.recommendation || (score <= 4 ? 'cut' : 'keep');
                    const isChecked = recommendation === 'cut';

                    const div = document.createElement('div');
                    div.className = `flex items-start gap-3 p-3 rounded border ${isChecked ? 'bg-red-950/30 border-red-800' : 'bg-[#0a0a0a] border-[#222]'}`;
                    div.innerHTML = `
                        <input type="checkbox" id="cut-${idx}" class="cut-checkbox mt-1 w-5 h-5 cursor-pointer" 
                            data-start="${seg.start}" data-end="${seg.end}" ${isChecked ? 'checked' : ''}>
                        <div class="flex-1">
                            <div class="flex items-center gap-2 mb-1">
                                <span class="font-bold" style="color: ${scoreColor}">${score}/10</span>
                                <label for="cut-${idx}" class="text-sm font-semibold text-white cursor-pointer">
                                    ${seg.start}s - ${seg.end}s
                                </label>
                                <span class="text-xs px-2 py-0.5 rounded ${isChecked ? 'bg-red-800 text-red-200' : 'bg-green-800 text-green-200'}">
                                    ${isChecked ? 'CUT' : 'KEEP'}
                                </span>
                            </div>
                            <p class="text-xs text-gray-400">${seg.reason || seg.description || 'No reason provided'}</p>
                        </div>
                    `;

                    // Toggle styling on checkbox change
                    const checkbox = div.querySelector('input');
                    checkbox.addEventListener('change', () => {
                        const badge = div.querySelector('span:last-of-type');
                        if (checkbox.checked) {
                            div.classList.remove('bg-[#0a0a0a]', 'border-[#222]');
                            div.classList.add('bg-red-950/30', 'border-red-800');
                            badge.className = 'text-xs px-2 py-0.5 rounded bg-red-800 text-red-200';
                            badge.innerText = 'CUT';
                        } else {
                            div.classList.remove('bg-red-950/30', 'border-red-800');
                            div.classList.add('bg-[#0a0a0a]', 'border-[#222]');
                            badge.className = 'text-xs px-2 py-0.5 rounded bg-green-800 text-green-200';
                            badge.innerText = 'KEEP';
                        }
                    });

                    reviewCuts.appendChild(div);
                });
            }

            // Fetch duration for cut inversion
            const statusRes = await fetch(`/api/status/${videoId}`);
            const statusData = await statusRes.json();
            window.currentVideoDuration = statusData.phase_one_metadata?.duration || 0;

            // Apply AI Suggested Music automatically
            if (statusData.ai_suggested_music) {
                const suggested = statusData.ai_suggested_music;
                selectedMusicFile = suggested.id; // Use ID for download/selection
                if (selectedMusicName) selectedMusicName.innerText = `AI PICKED: ${suggested.title}`;
                if (addMusicToggle) addMusicToggle.checked = true;
                if (musicOptions) musicOptions.classList.remove('hidden');
            }

        } catch (e) {
            console.error(e);
            reviewSummary.innerText = "Error loading analysis.";
        }
    }

    function showError(msg) {
        if (errorText) {
            errorText.classList.remove('hidden');
            errorText.innerText = msg;
        }
        updateProgress(100, 'ERROR');
    }

    function handleCompletion(data) {
        if (errorText) errorText.classList.add('hidden');

        // Fetch captions if available
        if (data.captions_url) {
            fetch(data.captions_url)
                .then(res => res.json())
                .then(d => {
                    captionsData = d;
                    if (captionsData?.stylePreset) {
                        setActiveStyleButton(captionsData.stylePreset);
                    }
                })
                .catch(e => console.error(e));
        }

        setTimeout(() => {
            processingContainer.classList.add('hidden');
            resultContainer.classList.remove('hidden');

            resultVideo.src = data.output_url;
            downloadBtn.href = `/api/download/${data.output_url.split('/').pop()}`;
            resultVideo.play().catch(e => console.log("Auto-play prevented"));
        }, 500);
    }

    // Overwrite the listener for confirmRenderBtn to include logic
    if (confirmRenderBtn) {
        // Remove old listener if any (not possible here easily, but we are replacing the whole block)
        // We will just define the click handler here properly.
        confirmRenderBtn.onclick = async () => {
            if (!currentVideoId) return;

            // 1. Identify parts to REMOVE
            const removeRanges = [];
            document.querySelectorAll('.cut-checkbox:checked').forEach(cb => {
                removeRanges.push({
                    start: parseFloat(cb.dataset.start),
                    end: parseFloat(cb.dataset.end)
                });
            });

            // 2. Calculate parts to KEEP (Invert)
            // If no duration, we can't invert safely.
            const duration = window.currentVideoDuration || 99999;

            // Sort remove ranges
            removeRanges.sort((a, b) => a.start - b.start);

            const keepSegments = [];
            let currentPos = 0;

            removeRanges.forEach(range => {
                if (range.start > currentPos) {
                    keepSegments.push({ start: currentPos, end: range.start });
                }
                currentPos = Math.max(currentPos, range.end);
            });

            if (currentPos < duration) {
                keepSegments.push({ start: currentPos, end: duration });
            }

            // If no cuts checked, keepSegments should be empty to imply "keep all" or just one full segment?
            // Backend: if custom_segments provided, it uses ONLY those.
            // So if removeRanges is empty, we should send empty custom_segments?
            // No, if removeRanges is empty, we want to keep EVERYTHING.
            // If we send empty custom_segments, backend might default to "trim_boring_parts" logic again?
            // No, render_video_pipeline takes custom_segments. If empty, it checks...
            // Wait, render_video_pipeline: "if valid_custom_segments... else ... if not applied_ranges: keep full"
            // So if we send empty list, it keeps full video. Correct.

            const finalSegments = removeRanges.length > 0 ? keepSegments : [];

            // Gather params
            const transcript = reviewTranscript.value;
            const burnSubs = document.getElementById('burn-subs-toggle').checked;

            // UI Update
            reviewContainer.classList.add('hidden');
            processingContainer.classList.remove('hidden');
            updateProgress(50, 'RENDERING REALITY...');

            // Start Polling again
            pollStatus(currentVideoId);

            try {
                const res = await fetch('/api/render', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_id: currentVideoId,
                        custom_segments: finalSegments,
                        manual_transcript: transcript,
                        style_preset: selectedStyle,
                        add_subtitles: burnSubs,
                        platform: selectedPlatform,
                        format: selectedFormat,
                        aspect_ratio: customAspect ? `${customAspect.w}:${customAspect.h}` : (selectedCropPreset || selectedAspect),
                        resolution: selectedRes,
                        rotation: rotationDeg,
                        flip_horizontal: flipHorizontal
                    })
                });
                const d = await res.json();
                if (!d.success) throw new Error(d.message);

            } catch (e) {
                console.error(e);
                showError(e.message);
            }
        };
    }

    function renderCaptions(currentTime) {
        if (!captionOverlay || !captionsData || !captionsData.captions) return;

        const activeStyle = (captionsData.stylePreset || selectedStyle || 'sleek').toLowerCase();

        const currentCaption = captionsData.captions.find(c =>
            currentTime >= c.start && currentTime <= c.end
        );

        captionOverlay.innerHTML = '';

        if (currentCaption) {
            const el = document.createElement('div');
            // Map style presets to CSS classes
            // We need to ensure these classes exist in style.css or add them dynamically
            // For now, let's use inline styles or basic classes
            el.className = `caption-line style-${activeStyle}`;

            // Apply some base styles if not in CSS
            el.style.position = 'absolute';
            el.style.bottom = '10%';
            el.style.textAlign = 'center';
            el.style.width = '100%';
            el.style.pointerEvents = 'none';
            el.style.textShadow = '0 2px 4px rgba(0,0,0,0.8)';

            // Style specific adjustments (can be moved to CSS later)
            if (activeStyle === 'sleek') {
                el.style.fontFamily = "'Inter', sans-serif";
                el.style.fontWeight = '800';
                el.style.fontSize = '24px';
                el.style.color = 'white';
            } else if (activeStyle === 'minimal') {
                el.style.fontFamily = "'JetBrains Mono', monospace";
                el.style.fontSize = '18px';
                el.style.background = 'rgba(0,0,0,0.7)';
                el.style.padding = '4px 8px';
                el.style.borderRadius = '4px';
            } else if (activeStyle === 'meme') {
                el.style.fontFamily = "Impact, sans-serif";
                el.style.fontSize = '32px';
                el.style.color = 'white';
                el.style.webkitTextStroke = '2px black';
                el.style.textTransform = 'uppercase';
            } else if (activeStyle === 'neon') {
                el.style.fontFamily = "'Courier New', monospace";
                el.style.fontSize = '24px';
                el.style.color = '#F4E04D';
                el.style.textShadow = '0 0 10px #F4E04D';
            }

            // Simple word rendering with fallback to plain text
            const words = Array.isArray(currentCaption.words) ? currentCaption.words : [];
            if (words.length > 0) {
                words.forEach(word => {
                    const span = document.createElement('span');
                    span.textContent = (word.text || word.word || '') + ' ';
                    if (currentTime >= word.start && currentTime <= word.end) {
                        span.style.opacity = '1';
                        if (activeStyle === 'sleek') span.style.color = '#F4E04D';
                    } else {
                        span.style.opacity = activeStyle === 'minimal' ? '0.5' : '1';
                    }
                    el.appendChild(span);
                });
            }

            if (!el.innerHTML) {
                el.textContent = currentCaption.text;
            }

            captionOverlay.appendChild(el);
        }
    }

    function setActiveStyleButton(style) {
        selectedStyle = (style || 'sleek').toLowerCase();
        document.querySelectorAll('.style-btn').forEach(b => {
            b.classList.remove(...styleButtonClasses.active);
            b.classList.add(...styleButtonClasses.inactive);
            if (b.dataset.style === selectedStyle) {
                b.classList.add(...styleButtonClasses.active);
                b.classList.remove(...styleButtonClasses.inactive);
            }
        });
    }

    async function reprocessWithParams(extraParams = {}, options = {}) {
        if (!currentVideoId) return;

        // Show inline rerun state and keep result visible
        if (rerunSpinner) rerunSpinner.classList.remove('hidden');
        if (rerunStatus) {
            rerunStatus.classList.remove('hidden');
            rerunStatus.innerText = 'Re-running with your changes...';
        }
        processingContainer.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        updateProgress(5, 'QUEUED...');
        if (errorText) {
            errorText.classList.add('hidden');
            errorText.innerText = '';
        }

        const trimBoring = document.getElementById('trim-toggle').checked;
        const burnSubs = document.getElementById('burn-subs-toggle').checked;
        const promptText = (manualPrompt?.value || promptSearch?.value || '').trim() || lastPrompt;
        lastPrompt = promptText || lastPrompt;

        const payload = {
            video_id: currentVideoId,
            style_preset: selectedStyle,
            add_subtitles: burnSubs,
            trim_boring_parts: trimBoring,
            user_prompt: options.keepPrompt === false ? undefined : (promptText || undefined),
            ...extraParams
        };

        try {
            const res = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!data.success) throw new Error(data.message);
            pollStatus(currentVideoId);
        } catch (err) {
            console.error(err);
            if (errorText) {
                errorText.classList.remove('hidden');
                errorText.innerText = `Error: ${err.message}`;
            }
        } finally {
            if (rerunSpinner) rerunSpinner.classList.add('hidden');
            if (rerunStatus) {
                rerunStatus.classList.add('hidden');
                rerunStatus.innerText = '';
            }
        }
    }

    function parseCuts(text) {
        const lines = (text || '').split('\n').map(l => l.trim()).filter(Boolean);
        const segments = [];
        lines.forEach(line => {
            const parts = line.split('-').map(p => p.trim());
            if (parts.length !== 2) return;
            const start = parseFloat(parts[0]);
            const end = parseFloat(parts[1]);
            if (!isNaN(start) && !isNaN(end) && end > start) {
                segments.push({ start, end });
            }
        });
        return segments;
    }

    function showPopup(isComplete = false, downloadUrl = null) {
        billPopup.classList.remove('hidden');

        // Update popup content
        const title = billPopup.querySelector('h2');
        const desc = billPopup.querySelector('p');
        const actionBtn = document.getElementById('popup-action-btn');

        if (isComplete) {
            // This path is currently unused as we show the player instead
            // But keeping it for fallback
            title.innerText = "REALITY IS AN ILLUSION!";
            desc.innerText = "Your video has been processed. The universe is a hologram. Buy gold!";
            if (actionBtn) actionBtn.innerText = "CLOSE";
        } else {
            // Triangle click
            title.innerText = "I'M WATCHING YOU!";
            desc.innerText = "Remember: trust no one! Not even your video editor!";
            if (actionBtn) actionBtn.innerText = "CLOSE";
        }

        setTimeout(() => {
            billPopup.classList.remove('opacity-0');
            billPopupContent.classList.remove('scale-90', 'opacity-0', 'translate-y-10');
            billPopupContent.classList.add('scale-100', 'opacity-100', 'translate-y-0');
        }, 50);
    }

    function closePopup() {
        billPopup.classList.add('opacity-0');
        billPopupContent.classList.remove('scale-100', 'opacity-100', 'translate-y-0');
        billPopupContent.classList.add('scale-90', 'opacity-0', 'translate-y-10');
        setTimeout(() => {
            billPopup.classList.add('hidden');
        }, 300);
    }

    // --- Effects ---

    async function pingBackend() {
        try {
            const res = await fetch('/api', { method: 'GET' });
            return res.ok;
        } catch (e) {
            console.error('Health check failed', e);
            return false;
        }
    }

    function initGlitchEffect() {
        const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+";

        function scrambleText(element) {
            const originalText = element.getAttribute('data-text');
            let iteration = 0;
            let interval = null;

            clearInterval(element.dataset.intervalId);

            interval = setInterval(() => {
                element.innerText = originalText
                    .split("")
                    .map((letter, index) => {
                        if (index < iteration) {
                            return originalText[index];
                        }
                        return chars[Math.floor(Math.random() * chars.length)];
                    })
                    .join("");

                if (iteration >= originalText.length) {
                    clearInterval(interval);
                }

                iteration += 1 / 3;
            }, 30);

            element.dataset.intervalId = interval;
        }

        document.querySelectorAll('.glitch-text').forEach(el => {
            scrambleText(el);
            setInterval(() => {
                if (Math.random() > 0.9) scrambleText(el);
            }, 5000);
        });
    }

    function initBillBackground() {
        const billBg = document.getElementById('bill-bg');
        const billEyeBg = document.getElementById('bill-eye-bg');

        if (uploadContainer && billBg) {
            uploadContainer.addEventListener('mouseenter', () => {
                billBg.classList.remove('opacity-0');
                billBg.classList.add('opacity-100');
            });

            uploadContainer.addEventListener('mouseleave', () => {
                billBg.classList.remove('opacity-100');
                billBg.classList.add('opacity-0');
            });
        }

        window.addEventListener('mousemove', (e) => {
            const x = (e.clientX / window.innerWidth) * 20 - 10;
            const y = (e.clientY / window.innerHeight) * 20 - 10;

            if (billEyeBg) {
                billEyeBg.style.transform = `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`;
            }
        });
    }

    // --- Audio Library Modal Logic ---
    const audioLibraryModal = document.getElementById('audio-library-modal');
    const openAudioLibraryBtn = document.getElementById('open-audio-library');
    const closeAudioLibraryBtn = document.getElementById('close-audio-library');
    const audioListContainer = document.getElementById('audio-list-container');
    const musicSearchInput = document.getElementById('music-search-input');
    const musicSearchBtn = document.getElementById('music-search-btn');
    const playingTrackIndicator = document.getElementById('playing-track-indicator');
    const playingTrackName = document.getElementById('playing-track-name');
    const stopPreviewBtn = document.getElementById('stop-preview');

    if (openAudioLibraryBtn) {
        openAudioLibraryBtn.addEventListener('click', (e) => {
            e.preventDefault();
            audioLibraryModal.classList.remove('hidden');
            loadRecommendedMusic();
        });
    }

    if (closeAudioLibraryBtn) {
        closeAudioLibraryBtn.addEventListener('click', () => {
            audioLibraryModal.classList.add('hidden');
        });
    }

    // Search on button click or Enter key
    if (musicSearchBtn) {
        musicSearchBtn.addEventListener('click', () => searchMusic(musicSearchInput.value));
    }
    if (musicSearchInput) {
        musicSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') searchMusic(musicSearchInput.value);
        });
    }

    // Playlist cards trigger specific searches
    document.querySelectorAll('.playlist-card').forEach(card => {
        card.addEventListener('click', () => {
            const query = card.dataset.query;
            if (musicSearchInput) musicSearchInput.value = query;
            searchMusic(query);
        });
    });

    async function loadRecommendedMusic() {
        const promptText = (manualPrompt?.value || promptSearch?.value || '').trim();
        searchMusic(promptText || "trending tiktok viral");
    }

    async function searchMusic(query) {
        if (!query) return;

        // Show loading state
        audioListContainer.innerHTML = `
            <tr>
                <td colspan="6" class="py-20 text-center">
                    <div class="flex flex-col items-center gap-4">
                        <div class="w-10 h-10 border-4 border-gray-100 border-t-black rounded-full animate-spin"></div>
                        <p class="text-gray-400 font-bold text-sm uppercase tracking-widest">Searching the sound waves...</p>
                    </div>
                </td>
            </tr>
        `;

        try {
            const res = await fetch('/api/music/agent/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: query, video_id: currentVideoId })
            });
            const data = await res.json();

            if (data.success && data.tracks.length > 0) {
                renderAudioList(data.tracks);
            } else {
                audioListContainer.innerHTML = `<tr><td colspan="6" class="py-20 text-center text-gray-500 font-bold">No tracks found for "${query}"</td></tr>`;
            }
        } catch (err) {
            console.error('Search failed:', err);
            audioListContainer.innerHTML = `<tr><td colspan="6" class="py-20 text-center text-red-500 font-bold">Error searching music</td></tr>`;
        }
    }

    function renderAudioList(tracks) {
        audioListContainer.innerHTML = '';
        tracks.forEach(track => {
            const tr = document.createElement('tr');
            tr.className = "p-4 border-b border-gray-50 hover:bg-gray-50 transition-colors group";

            // Format duration
            const mins = Math.floor(track.duration / 60);
            const secs = Math.floor(track.duration % 60).toString().padStart(2, '0');
            const durationStr = `${mins}:${secs}`;

            tr.innerHTML = `
                <td class="px-4 py-4">
                    <div class="flex items-center gap-4">
                        <div class="relative w-12 h-12 rounded bg-black flex-shrink-0 overflow-hidden">
                            <img src="${track.thumbnail_url || 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=100&h=100&fit=crop'}" class="w-full h-full object-cover">
                        </div>
                        <div class="flex flex-col">
                            <span class="font-bold text-sm line-clamp-1">${track.title}</span>
                            <span class="text-xs font-bold text-red-500 uppercase tracking-tighter mt-1 group-hover:block transition-all">Use in Project Editor</span>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-4"></td>
                <td class="px-4 py-4 text-sm font-bold text-gray-400">${track.artist}</td>
                <td class="px-4 py-4 text-sm font-bold text-gray-500">${durationStr}</td>
                <td class="px-4 py-4">
                    <div class="flex gap-2">
                        <i data-lucide="video" class="w-4 h-4 text-gray-400"></i>
                        <i data-lucide="music" class="w-4 h-4 text-gray-400"></i>
                    </div>
                </td>
                <td class="px-4 py-4 text-right">
                    <button class="use-music-btn bg-black text-white px-5 py-2 rounded-full text-xs font-bold hover:bg-gray-800 transition-colors" data-id="${track.id}" data-title="${track.title}">
                        USE
                    </button>
                </td>
            `;

            // Use button logic
            tr.querySelector('.use-music-btn').addEventListener('click', () => {
                selectTrack(track);
            });

            audioListContainer.appendChild(tr);
        });
        lucide.createIcons();
    }

    async function selectTrack(track) {
        const trackId = track.id;
        const btn = audioListContainer.querySelector(`button[data-id="${trackId}"]`);
        const originalText = btn.innerText;
        btn.innerText = 'SELECTING...';
        btn.disabled = true;

        try {
            const res = await fetch('/api/music/agent/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ track_id: trackId, video_id: currentVideoId })
            });
            const data = await res.json();

            if (data.success) {
                // Update the main selection UI
                await loadAvailableMusic();
                if (musicSelect) {
                    musicSelect.value = data.filename;
                    selectedMusicFile = data.filename;
                    if (selectedMusicName) selectedMusicName.innerText = track.title || data.filename;
                }
                if (addMusicToggle) addMusicToggle.checked = true;
                if (musicOptions) musicOptions.classList.remove('hidden');

                // Close modal
                audioLibraryModal.classList.add('hidden');

                // Show indicator in main UI if possible or just alert
                console.log('Selected track:', data.filename);
            }
        } catch (err) {
            console.error('Selection failed:', err);
            btn.innerText = 'ERROR';
            setTimeout(() => {
                btn.innerText = originalText;
                btn.disabled = false;
            }, 2000);
        }
    }

    if (stopPreviewBtn) {
        stopPreviewBtn.addEventListener('click', () => {
            playingTrackIndicator.classList.add('hidden');
            // Here you'd stop the audio element if we had one for previews
        });
    }

    function initWaveSurfer() {
        if (document.getElementById('timeline-container')) {
            try {
                wavesurfer = WaveSurfer.create({
                    container: '#timeline-container',
                    waveColor: '#4b5563',
                    progressColor: '#F4E04D',
                    cursorColor: '#F4E04D',
                    barWidth: 2,
                    barRadius: 3,
                    cursorWidth: 1,
                    height: 80,
                    barGap: 3
                });
            } catch (e) {
                console.warn("Wavesurfer init failed", e);
            }
        }
    }

    function initProgressWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${window.location.host}/ws/progress`;

        try {
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('🔌 Progress WebSocket connected');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    // Update UI if this is for our current video
                    if (data.video_id === currentVideoId) {
                        updateProgress(data.progress, data.message);
                    }
                } catch (e) {
                    console.warn('WS message parse error', e);
                }
            };

            ws.onclose = () => {
                console.log('🔌 Progress WebSocket closed, reconnecting in 5s...');
                setTimeout(initProgressWebSocket, 5000);
            };

            ws.onerror = (err) => {
                console.warn('WebSocket error:', err);
            };
        } catch (e) {
            console.warn('WebSocket init failed:', e);
        }
    }
});
