# PraSush Avatar Customization Guide

## Current Avatar
PraSush currently uses a procedurally-generated animated avatar drawn with Pygame primitives (circles, ellipses, arcs).

## Custom Avatar Features (Planned Upgrades)

If you provide a 3D-looking image or avatar, we can implement:

### 1. **Avatar Image Integration**
- Replace the procedural avatar with your custom image
- Display as a PNG/JPEG/GIF on the screen
- Scale to fit the display window

**How to use:**
1. Create or find a 3D avatar image (PNG with transparency recommended)
2. Save it as `ui/avatar.png` in the project folder
3. We'll update the display code to render your image instead of the procedural one

### 2. **Head Rotation Animation**
- Rotate the avatar head left/right based on conversation flow or emotion
- 3D depth effect if the original image supports it

**Implementation:**
- Use `cv2.warpAffine()` or PIL `Image.rotate()` for rotation
- Rotate ±15-20° during listening, thinking, or responding modes
- Can be tied to speech recognition confidence

### 3. **Mouth Movement (Lip-Sync)**
- Animate lips to match spoken text
- Extract phonemes from the text being spoken
- Apply mouth shapes: closed, open, "o", "ee", etc.

**Implementation:**
- Use automatic mouth shape mapping based on phoneme detection
- Simple frame-based animation with different mouth images per phoneme
- Pre-render 6-8 mouth shapes for your avatar

### 4. **Eye Movement & Blinking**
- Eyes look in different directions during thinking, listening, speaking
- Periodic blinking for natural look
- Focus on the user or camera if visual question asked

**Implementation:**
- Define eye positions within the image
- Move eye position based on context (left = thinking, straight = listening, right = observing)
- Blink every 3-5 seconds

### 5. **Head Thinking Animation**
- Slight head tilt or rotation when processing a question
- "Nod" gesture when receiving information
- Head shake for uncertainty or errors

**Implementation:**
- Combine rotation + slight vertical offset
- Trigger during "Thinking..." display state
- Smooth animation over 1-2 seconds

---

## Steps to Implement Custom Avatar

### Step 1: Prepare Your Image
- Get a 3D avatar image (find on Sketchfab, create with Blender, or use AI generation tools)
- Recommendations:
  - Size: 600x800 pixels (height > width for portrait orientation)
  - Format: PNG with transparent background
  - Art style: Cartoon, anime, stylized 3D, or realistic
- Save as: `ui/avatar/avatar.png`

### Step 2: Create Mouth Shapes (Optional but recommended)
For realistic lip-sync, create 8 mouth variations:
- `mouth_01_closed.png` - Closed mouth (neutral)
- `mouth_02_open.png` - Open "ah" sound
- `mouth_03_o.png` - "O" shape (oh, oo sounds)
- `mouth_04_ee.png` - "EE" shape (smiling, ee sounds)
- `mouth_05_m.png` - "M" shape (m, b, p sounds)
- `mouth_06_f.png` - "F" shape (f, v sounds)
- `mouth_07_surprise.png` - Wide open (surprised)
- `mouth_08_smile.png` - Happy/speaking

Save in: `ui/avatar/mouths/`

### Step 3: Create Eye Positions File
Create `ui/avatar/eyes.json`:
```json
{
  "left_eye": {
    "center": [150, 200],
    "width": 40,
    "height": 50
  },
  "right_eye": {
    "center": [450, 200],
    "width": 40,
    "height": 50
  },
  "head_position": [300, 300],
  "head_rotation_center": [300, 250]
}
```

### Step 4: Update Display Code
We'll modify `ui/display.py` to:
- Load your avatar image
- Render head rotation based on state
- Swap mouth images during speech
- Move eyes based on interaction context
- Handle blinking animation

---

## Integration Timeline

1. **Basic Custom Avatar** (Easy - 1 hour)
   - Replace procedural avatar with your image
   - Simple scaling and positioning

2. **Head Rotation** (Medium - 2 hours)
   - Add rotation animation during thinking
   - Link to app states (listening, thinking, speaking)

3. **Mouth Movement** (Medium - 3 hours)
   - Create mouth shape files
   - Implement phoneme-to-mouth mapping
   - Integrate with speech synthesis

4. **Eyes & Blinking** (Medium - 2 hours)
   - Eye tracking (look at microphone when listening, camera when observing)
   - Periodic blinking with custom eye positions

5. **Full Thinking Animation** (Easy - 1 hour)
   - Combined head tilt + rotation
   - Smooth transitions between states

---

## Example: Custom Avatar JSON Config

Create `ui/avatar/config.json`:
```json
{
  "name": "PraSush Custom Avatar",
  "image": "avatar.png",
  "scale": 1.0,
  "position": {
    "x": "center",
    "y": "center_lower"
  },
  "animations": {
    "head_rotation": true,
    "mouth_sync": true,
    "eye_tracking": true,
    "blinking": true,
    "thinking_tilt": true
  },
  "emotions": {
    "default": {
      "head_tilt": 0,
      "mouth": "closed",
      "eyes": "straight"
    },
    "thinking": {
      "head_tilt": 10,
      "mouth": "closed",
      "eyes": "up_left"
    },
    "happy": {
      "head_tilt": 0,
      "mouth": "smile",
      "eyes": "happy"
    }
  }
}
```

---

## Getting Avatar Images

### Free Resources:
1. **Sketchfab** (sketchfab.com) - Free 3D models, export as PNG
2. **itch.io** - Free game-ready character assets
3. **OpenGameArt.org** - Open-source game art
4. **AI Generation**:
   - DALL-E: "Cute 3D animated avatar, portrait style, transparent background"
   - Midjourney: Similar prompts
   - Stable Diffusion: LocalDiffusion for offline generation

### Commercial Options:
- Ready Player Me (readyplayer.me) - Free 3D avatars
- Character Creator by Reallusion
- VRoid Studio - Free anime character creation

---

## Next Steps

When you're ready:
1. **Provide your avatar image** (PNG recommended)
2. **We'll integrate it** into the display system
3. **Add animations** one by one
4. **Test and refine** together

The system will be fully modular, so you can swap avatars easily or adjust animations on the fly!

---

## Current Display Code Location
- Main display logic: `ui/display.py` (line 50-100 for rendering)
- Avatar drawing: `_draw_avatar()` method (line 70+)
- Status/subtitle drawing: `_draw_status()` and `_draw_subtitle()` methods

Once you have your image, implementation is straightforward!
