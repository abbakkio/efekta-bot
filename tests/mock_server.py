from aiohttp import web

# Minimal base64 silent WAV audio data URI to supply a valid HTML5 audio track
SILENT_AUDIO_URI = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQQAAAAAAA=="

HTML_TEMPLATE = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Efekta Self-Study Simulated Portal</title>
  <style>
    body {{ font-family: sans-serif; padding: 30px; max-width: 600px; margin: auto; }}
    .slide {{ display: none; border: 1px solid #ccc; padding: 20px; border-radius: 8px; }}
    .active {{ display: block; }}
    button {{ padding: 10px 16px; margin: 8px 4px; cursor: pointer; }}
    .choice {{ display: block; width: 100%; text-align: left; }}
    .choice.selected {{ background-color: #d1e7dd; border-color: #badbcc; }}
  </style>
</head>
<body>
  <div id="step-login" class="slide active">
    <h2>Efekta Login</h2>
    <form id="login-form">
      <div><input type="email" name="username" placeholder="Email" value="student@example.com"></div>
      <div style="margin-top: 8px;"><input type="password" name="password" placeholder="Password" value="secret"></div>
      <div style="margin-top: 12px;"><button type="submit">Log in</button></div>
    </form>
  </div>

  <div id="step-media" class="slide">
    <h2>Step 1: Listening Task</h2>
    <p>Listen to the dialogue:</p>
    <audio id="audio-player" src="{SILENT_AUDIO_URI}" controls></audio>
    <div>
      <button id="media-next-btn" data-testid="next-btn" disabled>Next</button>
    </div>
  </div>

  <div id="step-speaking" class="slide">
    <h2>Step 2: Pronunciation Drill</h2>
    <p>Read aloud: <em>"Hello, nice to meet you."</em></p>
    <button id="record-btn" data-testid="record-btn">Record</button>
    <span id="recording-status">Idle</span>
    <div>
      <button id="speaking-next-btn" data-testid="next-btn" style="display:none;">Next</button>
    </div>
  </div>

  <div id="step-choice" class="slide">
    <h2>Step 3: Comprehension</h2>
    <p>What is the best greeting?</p>
    <button role="radio" class="choice" data-testid="choice-1">A) Good morning</button>
    <button role="radio" class="choice" data-testid="choice-2">B) Goodbye</button>
    <div>
      <button id="choice-check-btn" data-testid="check-btn">Check</button>
      <button id="choice-next-btn" data-testid="next-btn" style="display:none;">Next</button>
    </div>
  </div>

  <div id="step-finish" class="slide">
    <div class="unit-completed">
      <h1>Unit Complete</h1>
      <p>Congratulations on finishing the lesson!</p>
    </div>
  </div>

  <script>
    function showSlide(id) {{
      document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
      document.getElementById(id).classList.add('active');
    }}

    // Login logic
    document.getElementById('login-form').addEventListener('submit', (e) => {{
      e.preventDefault();
      showSlide('step-media');
    }});

    // Media logic: Enable next button when audio ends
    const audio = document.getElementById('audio-player');
    const mediaNext = document.getElementById('media-next-btn');
    audio.addEventListener('ended', () => {{
      mediaNext.disabled = false;
    }});
    mediaNext.addEventListener('click', () => {{
      showSlide('step-speaking');
    }});

    // Speaking logic: getUserMedia + MediaRecorder
    const recordBtn = document.getElementById('record-btn');
    const recordingStatus = document.getElementById('recording-status');
    const speakingNext = document.getElementById('speaking-next-btn');
    let recorder = null;

    recordBtn.addEventListener('click', async () => {{
      try {{
        const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        recordingStatus.textContent = "Recording...";
        recorder = new MediaRecorder(stream);
        recorder.start();
        setTimeout(() => {{
          recorder.stop();
          stream.getTracks().forEach(t => t.stop());
          recordingStatus.textContent = "Done!";
          speakingNext.style.display = "inline-block";
        }}, 2000);
      }} catch (err) {{
        recordingStatus.textContent = "Mic error: " + err;
      }}
    }});
    speakingNext.addEventListener('click', () => {{
      showSlide('step-choice');
    }});

    // Multiple Choice logic
    const choices = document.querySelectorAll('.choice');
    let selectedChoice = null;
    choices.forEach(btn => {{
      btn.addEventListener('click', () => {{
        choices.forEach(c => {{
          c.classList.remove('selected');
          c.setAttribute('aria-checked', 'false');
        }});
        btn.classList.add('selected');
        btn.setAttribute('aria-checked', 'true');
        selectedChoice = btn;
      }});
    }});

    const choiceCheck = document.getElementById('choice-check-btn');
    const choiceNext = document.getElementById('choice-next-btn');
    choiceCheck.addEventListener('click', () => {{
      if (selectedChoice) {{
        choiceCheck.style.display = 'none';
        choiceNext.style.display = 'inline-block';
      }}
    }});
    choiceNext.addEventListener('click', () => {{
      showSlide('step-finish');
    }});
  </script>
</body>
</html>
"""

async def handle_portal(request):
    return web.Response(text=HTML_TEMPLATE, content_type="text/html")

def create_mock_app():
    app = web.Application()
    app.router.add_get("/", handle_portal)
    app.router.add_get("/gap/ui/self-study", handle_portal)
    return app

if __name__ == "__main__":
    app = create_mock_app()
    web.run_app(app, port=8888)
