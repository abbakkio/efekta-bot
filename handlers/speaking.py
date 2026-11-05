import asyncio
import base64
import json
import os
import re
import subprocess
from patchright.async_api import Page, Frame, BrowserContext
from .base import BaseHandler

class SpeakingHandler(BaseHandler):
    """Handles speaking exercises using network-level TTS synthesis injection

    and smart option selection for multiple-choice speech tasks.
    """

    def __init__(self):
        super().__init__()
        self._task_attempts = {}
        self._last_detected_phrase = ""
        self._context_routed = set()
        self._failed_options_by_task = {}

    def _get_recorder_button(self, target: Page | Frame):
        return target.locator(
            'button[data-qa="audio-record-or-play"]:visible, '
            'button.audio-recorder-btn:visible, '
            'button:visible[aria-label*="record" i], '
            'button:visible[aria-label*="stop" i], '
            'button:visible[data-testid*="record" i], '
            'ef-audio-recorder button:not([aria-label*="replay" i]):visible'
        ).first

    def _get_skip_button(self, target: Page | Frame):
        return target.locator(
            'button.skip-task-button:visible, '
            'button:not([disabled]):visible:has-text("SKIP"), '
            'button:not([disabled]):visible:has-text("Skip"), '
            '[translation-key="activity.skip"]:visible, '
            '[ef-translate="activity.skip"]:visible'
        ).first

    def _find_speech_nodes(self, obj):
        nodes = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'speechData' and isinstance(v, dict):
                    nodes.append(v)
                elif isinstance(v, (dict, list)):
                    nodes.extend(self._find_speech_nodes(v))
        elif isinstance(obj, list):
            for item in obj:
                nodes.extend(self._find_speech_nodes(item))
        return nodes

    def _generate_wav(self, text: str) -> str:
        """Synthesizes text to a 16-bit 16kHz mono WAV file using macOS say command."""
        wav_path = f"/tmp/efekta_speech_{os.getpid()}.wav"
        clean_text = re.sub(r"[_]+", "", text)
        clean_text = clean_text.replace('"', '').replace('\n', ' ')
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if not clean_text:
            return ""

        try:
            subprocess.run([
                "say", "-v", "Samantha", "-o", wav_path, "--data-format=LEI16@16000", clean_text
            ], check=True, timeout=8)
        except Exception:
            try:
                subprocess.run([
                    "say", "-o", wav_path, "--data-format=LEI16@16000", clean_text
                ], check=True, timeout=8)
            except Exception as e:
                print(f"    [Speaking] Note: Failed to generate TTS audio ({e})")
                return ""

        if os.path.exists(wav_path):
            with open(wav_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        return ""

    def _intercept_and_synthesize_payload(self, payload: dict) -> bool:
        """Modifies payload to inject correct/untried options and synthesized audio."""
        modified = False
        cmd_data = payload.get('commandData', {})
        sub = cmd_data.get('submitTaskResponse', {})
        resp = sub.get('response', {})
        task_id = resp.get('taskId') or payload.get('taskId') or "generic_task"

        # 1. Handle Multiple-Choice Speech tasks (contents.multipleChoice.contents WITH speechData)
        mc = resp.get('contents', {}).get('multipleChoice', {}).get('contents', {})
        sd_mc = resp.get('contents', {}).get('multipleChoice', {}).get('speechData')
        if mc and isinstance(mc, dict) and sd_mc and isinstance(sd_mc, dict):
            failed = self._failed_options_by_task.setdefault(task_id, set())
            available = [oid for oid in mc if oid not in failed]
            if not available:
                failed.clear()
                available = list(mc.keys())

            chosen_oid = available[0]
            print(f"  [Speaking Route] Task {task_id[:8]}: Selecting option {chosen_oid[:8]} ({len(available)-1} remaining untried)")
            for oid in mc:
                mc[oid]['userInput'] = 'selected' if oid == chosen_oid else 'not-selected'
            modified = True

            # Synthesize speech for this chosen option phrase if textOptions are present
            text_opts = sd_mc.get('textOptions', {})
            for phrase, oid in text_opts.items():
                if oid == chosen_oid:
                    print(f"  [Speaking Route] Synthesizing speech for option: '{phrase}'")
                    b64 = self._generate_wav(phrase)
                    if b64:
                        sd_mc['data'] = b64
                    break

        # 2. Handle pure Speaking Practice tasks (speakingPractice.userInput)
        sp = resp.get('contents', {}).get('speakingPractice', {})
        if sp and isinstance(sp, dict):
            user_input = sp.get('userInput')
            if isinstance(user_input, dict):
                target_text = user_input.get('targetText') or user_input.get('text') or user_input.get('phrase')
                if not target_text and self._last_detected_phrase:
                    target_text = self._last_detected_phrase
                if target_text:
                    print(f"  [Speaking Route] Synthesizing speech for speakingPractice: '{target_text}'")
                    b64 = self._generate_wav(target_text)
                    if b64:
                        user_input['data'] = b64
                        modified = True

        # 3. Handle generic speechData nodes
        nodes = self._find_speech_nodes(payload)
        for sd in nodes:
            chosen_phrase = ""
            for k in ['text', 'targetText', 'expectedText', 'referenceText', 'phrase', 'sentence', 'prompt']:
                if k in sd and isinstance(sd[k], str) and sd[k].strip():
                    chosen_phrase = sd[k].strip()
                    break
            if not chosen_phrase and self._last_detected_phrase:
                chosen_phrase = self._last_detected_phrase

            if chosen_phrase:
                b64 = self._generate_wav(chosen_phrase)
                if b64:
                    sd['data'] = b64
                    modified = True

        return modified

    async def setup_context_routing(self, context: BrowserContext):
        """Attaches request interception on lesson commands to inject synthesized speech audio and track assessment."""
        ctx_id = id(context)
        if ctx_id in self._context_routed:
            return
        self._context_routed.add(ctx_id)

        async def route_handler(route):
            req = route.request
            if req.method == 'POST' and 'lesson/command' in req.url:
                post_data = req.post_data
                if post_data and 'submit-task-response' in post_data:
                    try:
                        payload = json.loads(post_data)
                        if self._intercept_and_synthesize_payload(payload):
                            new_body = json.dumps(payload)
                            await route.continue_(post_data=new_body)
                            return
                    except Exception as e:
                        print(f"  [Speaking Route Error] {e}")
            await route.continue_()

        # Listen to responses to learn which options were assessed as incorrect/correct
        def on_response(res):
            if 'lesson/command' in res.url:
                asyncio.create_task(self._process_command_response(res))

        try:
            await context.route('**/*lesson/command', route_handler)
            for page in context.pages:
                page.on('response', on_response)
            context.on('page', lambda page: page.on('response', on_response))
            print("  [Speaking] Attached route interception for speech commands.")
        except Exception as e:
            print(f"  [Speaking Route Attach Error] {e}")

    async def _process_command_response(self, res):
        try:
            text = await res.text()
            if 'taskResponseAssessed' in text:
                data = json.loads(text)
                for ev in data.get('eventHistory', {}).get('events', []):
                    tra = ev.get('data', {}).get('taskResponseAssessed', {})
                    if tra:
                        task_id = tra.get('response', {}).get('taskId')
                        mc = tra.get('response', {}).get('contents', {}).get('multipleChoice', {}).get('contents', {})
                        for oid, info in mc.items():
                            res_val = info.get('assessment', {}).get('result')
                            if res_val == 'incorrect' and task_id:
                                self._failed_options_by_task.setdefault(task_id, set()).add(oid)
        except Exception:
            pass

    async def can_handle(self, target: Page | Frame) -> bool:
        # 1. If Next or Continue is already enabled, let NavigationHandler advance
        advance_btn = target.locator(
            'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button[class*="main-next"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next"), '
            'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Continue"), '
            'button[data-testid*="next" i]:not([disabled]):visible, '
            'button[data-testid*="continue" i]:not([disabled]):visible'
        ).first
        if await advance_btn.count() > 0:
            return False

        # 2. If select mode (tap task) is active with clickable options, let MultipleChoiceHandler handle it
        clickable_options = target.locator(
            'ef-multiple-choice-tap-task-response-option button.option-button:not(.incorrect):visible, '
            'button[role="radio"]:not(.incorrect):visible'
        )
        if await clickable_options.count() > 0:
            return False

        # 3. Check for speech recorder button or speech task container
        rec_btn = self._get_recorder_button(target)
        if await rec_btn.count() > 0:
            return True

        speech_task = target.locator(
            'ef-multiple-choice-speech-task:visible, '
            'ef-speaking-practice-task:visible, '
            'ef-audio-recorder:visible'
        )
        if await speech_task.count() > 0:
            return True

        return False

    async def _extract_target_phrase(self, target: Page | Frame) -> str:
        """Extracts the exact target sentence or option for the active speech task."""
        # A. Check VISIBLE multiple choice speech task response options first (filtering out already marked incorrect)
        try:
            options_loc = target.locator("ef-multiple-choice-speech-task-response-option:not(.incorrect):visible label.content:visible")
            opt_count = await options_loc.count()
            if opt_count > 0:
                txt = (await options_loc.first.inner_text()).strip()
                if txt:
                    return txt
            # Fallback if all options were marked incorrect
            all_opts = target.locator("ef-multiple-choice-speech-task-response-option:visible label.content:visible")
            if await all_opts.count() > 0:
                txt = (await all_opts.first.inner_text()).strip()
                if txt:
                    return txt
        except Exception:
            pass

        # B. Check speaking task container text or text between Play audio and SKIP
        try:
            phrase = await target.evaluate("""() => {
                const uiTerms = ["play audio", "try again", "not quite right", "recording", "record the phrase", "pronunciation", "feedback", "skip", "next", "review", "need some help"];
                const isUi = (s) => {
                    const lower = (s || "").toLowerCase().trim();
                    return uiTerms.some(term => lower.includes(term)) || /^\\d+\\s*\\/\\s*\\d+$/.test(lower) || /^\\d+$/.test(lower);
                };

                const speakingTask = document.querySelector('ef-speaking-practice-task, ef-speech-recognition-task');
                if (speakingTask) {
                    const words = (speakingTask.innerText || "").split("\\n").map(s => s.trim()).filter(s => s && !isUi(s));
                    if (words.length > 0) return words.join(" ");
                }

                const body = document.body.innerText || "";
                const matchAfterAudio = body.match(/Play audio\\s*\\n([\\s\\S]+?)\\n\\s*(?:SKIP|Next|Pronunciation|Feedback|Recording)/i);
                if (matchAfterAudio) {
                    const lines = matchAfterAudio[1].split("\\n").map(s => s.trim()).filter(s => s && !isUi(s));
                    if (lines.length > 0) return lines.join(" ");
                }

                const matchHeader = body.match(/(?:Task \\d+ of \\d+|\\d+\\s*\\/\\s*\\d+)\\s*\\n([\\s\\S]+?)\\n\\s*(?:Play audio|SKIP|Recording|Pronunciation)/i);
                if (matchHeader) {
                    const lines = matchHeader[1].split("\\n").map(s => s.trim()).filter(s => s && !isUi(s));
                    if (lines.length > 0) return lines.join(" ");
                }

                return "";
            }""")
            if phrase and len(phrase.strip()) > 1:
                clean = phrase.strip()
                ui_words = ["play audio", "try again", "not quite right", "record the phrase"]
                if not any(u in clean.lower() for u in ui_words):
                    return clean
        except Exception:
            pass

        return ""

    def _speak_phrase_aloud(self, text: str):
        """Speaks the target phrase aloud using macOS TTS to supply audio to microphone."""
        if not text:
            return
        clean_p = re.sub(r"[_]+", "", text)
        clean_p = clean_p.replace('"', '').replace('\n', ' ')
        clean_p = re.sub(r"\s+", " ", clean_p).strip()
        if not clean_p:
            return
        print(f"  [Speaking] Speaking phrase aloud via TTS: '{clean_p[:50]}'...")
        try:
            p = subprocess.Popen(["say", "-v", "Samantha", clean_p])
            try:
                p.wait(timeout=4.0)
            except subprocess.TimeoutExpired:
                p.kill()
        except Exception as e:
            print(f"  [Speaking] Note: TTS speak aloud failed ({e})")

    async def _wait_for_evaluation(self, target: Page | Frame, timeout: float = 3.5):
        """Waits dynamically for Next button to become enabled or recorder to leave recording state."""
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            advance_btn = target.locator(
                'button[class*="next-task-button"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
                'button[class*="main-next"]:not([disabled]):not(.mat-mdc-button-disabled):visible, '
                'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Next"), '
                'button.mat-mdc-unelevated-button:not([disabled]):not(.mat-mdc-button-disabled):visible:has-text("Continue"), '
                'button[data-testid*="next" i]:not([disabled]):visible'
            ).first
            try:
                if await advance_btn.count() > 0 and not await advance_btn.is_disabled():
                    return True
            except Exception:
                pass

            rec_btn = self._get_recorder_button(target)
            try:
                if await rec_btn.count() > 0:
                    aria = (await rec_btn.get_attribute("aria-label") or "").lower()
                    has_replay = await target.locator('ef-svg-replay').count() > 0
                    if "not quite right" in aria or "try again" in aria or has_replay:
                        return True
            except Exception:
                pass

            await asyncio.sleep(0.3)
        return True

    async def handle(self, target: Page | Frame) -> bool:
        # Ensure context routing is attached
        try:
            page = target.page if isinstance(target, Frame) else target
            if page and page.context:
                await self.setup_context_routing(page.context)
        except Exception:
            pass

        # Also register any incorrect options currently visible in the DOM
        try:
            dom_incorrect = await target.evaluate("""() => {
                const el = document.querySelector('ef-multiple-choice-speech-task');
                const taskId = el ? el.getAttribute('taskid') : null;
                const incorrect = Array.from(document.querySelectorAll('ef-multiple-choice-speech-task-response-option.incorrect, ef-multiple-choice-speech-task-response-option[class*="incorrect"]')).map(o => o.getAttribute('optionid')).filter(Boolean);
                return { taskId, incorrect };
            }""")
            if dom_incorrect.get('taskId') and dom_incorrect.get('incorrect'):
                t_id = dom_incorrect['taskId']
                for oid in dom_incorrect['incorrect']:
                    self._failed_options_by_task.setdefault(t_id, set()).add(oid)
        except Exception:
            pass

        detected = await self._extract_target_phrase(target)
        if detected:
            self._last_detected_phrase = detected

        rec_btn = self._get_recorder_button(target)
        skip_btn = self._get_skip_button(target)

        task_sig = ""
        try:
            task_sig = await target.evaluate("""() => {
                const m = (document.body.innerText || '').match(/(?:Task \\d+ of \\d+|\\d+\\s*\\/\\s*\\d+)/i);
                return m ? m[0].replace(/\\s+/g, '') : '';
            }""")
        except Exception:
            pass

        phrase_key = task_sig if task_sig else (detected[:40] if detected else "generic_speech_task")

        aria_label = ""
        is_recording = False
        has_replay = False
        if await rec_btn.count() > 0:
            aria_label = (await rec_btn.get_attribute("aria-label") or "").lower()
            is_recording = await rec_btn.locator('ef-svg-stop').count() > 0 or "recording" in aria_label or "stop" in aria_label
            has_replay = await target.locator('ef-svg-replay').count() > 0

        # Reset attempts counter if task is fresh / ready to record
        if "click to record" in aria_label or "record your" in aria_label or (not is_recording and not has_replay and "not quite" not in aria_label and "try again" not in aria_label):
            if not has_replay and "not quite" not in aria_label and "try again" not in aria_label:
                if "click to record" in aria_label or "record your" in aria_label:
                    self._task_attempts[phrase_key] = 0

        attempts = self._task_attempts.get(phrase_key, 0)

        is_mc_speech = await target.locator('ef-multiple-choice-speech-task:visible').count() > 0
        mc_options_count = await target.locator('ef-multiple-choice-speech-task-response-option:visible').count()
        max_attempts = mc_options_count if is_mc_speech and mc_options_count > 0 else 1

        # 1. Check if the recorder is explicitly evaluated as incorrect
        is_evaluated_incorrect = "not quite right" in aria_label or "try again" in aria_label or has_replay

        # 2. Advance via SKIP only if:
        #    a) pure speaking practice evaluated as incorrect, OR
        #    b) attempt threshold reached on multiple choice speech task
        should_skip = False
        if is_evaluated_incorrect and not is_mc_speech:
            should_skip = True
        elif attempts >= max_attempts:
            should_skip = True

        if should_skip and await skip_btn.count() > 0:
            print(f"  [Speaking] Task evaluated as incorrect or attempt threshold ({attempts}/{max_attempts}) reached. Advancing via SKIP...")
            await self.sleep_delay(0.2, 0.4)
            try:
                await skip_btn.click(timeout=3000)
            except Exception:
                try:
                    await skip_btn.dispatch_event("click", timeout=3000)
                except Exception:
                    pass
            await self.sleep_delay(1.0, 1.5)
            self._task_attempts[phrase_key] = 0
            return True

        # 3. Handle active recording in progress (e.g. Efekta auto-started recording)
        if await rec_btn.count() > 0:
            if is_recording:
                print("  [Speaking] Recording in progress. Speaking phrase aloud...")
                self._speak_phrase_aloud(detected or self._last_detected_phrase)
                await asyncio.sleep(0.3)
                stop_btn = self._get_recorder_button(target)
                if await stop_btn.count() > 0:
                    print("  [Speaking] Stopping recording for evaluation...")
                    try:
                        await stop_btn.click(timeout=3000)
                    except Exception:
                        try:
                            await stop_btn.dispatch_event("click", timeout=3000)
                        except Exception:
                            pass
                await self._wait_for_evaluation(target)
                self._task_attempts[phrase_key] = attempts + 1
                return True

            # 4. Trigger new recording attempt (for fresh task or next MC option)
            if not is_evaluated_incorrect or is_mc_speech:
                print("  [Speaking] Triggering recording...")
                try:
                    await rec_btn.click(timeout=3000)
                except Exception:
                    try:
                        await rec_btn.dispatch_event("click", timeout=3000)
                    except Exception:
                        pass

                await asyncio.sleep(0.3)
                self._speak_phrase_aloud(detected or self._last_detected_phrase)
                await asyncio.sleep(0.3)

                stop_btn = self._get_recorder_button(target)
                if await stop_btn.count() > 0:
                    stop_aria = (await stop_btn.get_attribute("aria-label") or "").lower()
                    if "recording" in stop_aria or "stop" in stop_aria or await stop_btn.locator('ef-svg-stop').count() > 0:
                        print("  [Speaking] Stopping recording for evaluation...")
                        try:
                            await stop_btn.click(timeout=3000)
                        except Exception:
                            try:
                                await stop_btn.dispatch_event("click", timeout=3000)
                            except Exception:
                                pass

                await self._wait_for_evaluation(target)
                self._task_attempts[phrase_key] = attempts + 1
                return True

        # 5. Fallback: only if no recorder button exists and SKIP is available
        if await rec_btn.count() == 0 and await skip_btn.count() > 0:
            print("  [Speaking] No recorder button found. Advancing via SKIP...")
            await self.sleep_delay(0.2, 0.4)
            try:
                await skip_btn.click(timeout=3000)
            except Exception:
                try:
                    await skip_btn.dispatch_event("click", timeout=3000)
                except Exception:
                    pass
            await self.sleep_delay(1.0, 1.5)
            return True

        return False
