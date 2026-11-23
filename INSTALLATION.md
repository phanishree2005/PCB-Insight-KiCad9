# KiCad 9 Plugin Installation & Setup Guide
**Project:** PCB Insight – Intelligent PCB Design Analyzer for KiCad 9  
**Document ID:** INST-001  

---

## 1. Prerequisites
- **KiCad Version:** KiCad 9.0.0 or later (Verify via `kicad-cli --version` or KiCad Help > About).
- **Python Version:** Python 3.9 or later (KiCad 9 standard environment uses Python 3.10+).
- **Operating System:** Windows 10/11, Linux (Ubuntu 22.04+, Fedora 38+), or macOS (12+).

---

## 2. Installation Architecture Pathways

PCB Insight supports both modern KiCad 9 IPC plugins and classic KiCad Action Plugins. Choose the installation method matching your workflow:

---

### Option A: Modern KiCad 9 IPC Plugin (Recommended)

KiCad 9 supports out-of-process plugins declared via a `plugin.json` manifest.

1. **Enable the IPC API Server in KiCad:**
   - Open KiCad 9.
   - Go to **Preferences > Plugins**.
   - Check the box **Enable API Server**.
   - Click **OK**.

2. **Install Dependencies:**
   Install `kicad-python` into your Python environment:
   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy the Plugin Manifest:**
   Copy the `PCB-Insight-KiCad9` directory into KiCad 9's 3rd-party plugins directory:

   - **Windows:**
     ```powershell
     # Default KiCad 9 3rd-party plugin directory
     $targetDir = "$env:APPDATA\kicad\9.0\plugins\org.fossee.pcb_insight"
     New-Item -ItemType Directory -Force -Path $targetDir
     Copy-Item -Recurse -Force ./* $targetDir
     ```

   - **Linux:**
     ```bash
     mkdir -p ~/.local/share/kicad/9.0/plugins/org.fossee.pcb_insight
     cp -r ./* ~/.local/share/kicad/9.0/plugins/org.fossee.pcb_insight/
     ```

   - **macOS:**
     ```bash
     mkdir -p ~/Library/Application\ Support/kicad/9.0/plugins/org.fossee.pcb_insight
     cp -r ./* ~/Library/Application\ Support/kicad/9.0/plugins/org.fossee.pcb_insight/
     ```

4. **Restart KiCad:**
   Launch the PCB Editor. The PCB Insight button will appear in the top action toolbar.

---

### Option B: Legacy KiCad 9 Action Plugin (Fallback)

For standard KiCad 9 installations using in-editor Action Plugins:

1. Locate KiCad's scripting plugins directory:
   - **Windows:** `%APPDATA%\kicad\9.0\scripting\plugins`
   - **Linux:** `~/.local/share/kicad/9.0/scripting/plugins`
   - **macOS:** `~/Library/Application Support/kicad/9.0/scripting/plugins`

2. Symlink or copy the `pcb_insight` folder into the scripting plugins directory:
   ```powershell
   # Windows PowerShell (Run as Administrator or Developer Mode)
   New-Item -ItemType SymbolicLink -Path "$env:APPDATA\kicad\9.0\scripting\plugins\pcb_insight" -Target "$PWD\pcb_insight"
   ```

3. In KiCad PCB Editor:
   - Go to **Tools > External Plugins > Refresh Plugins**.
   - Select **Tools > External Plugins > PCB Insight**.

---

### Option C: Standalone Headless / CLI Usage

To analyze `.kicad_pcb` files directly from the command line without opening KiCad:

```bash
# Analyze board and view terminal summary
python -m pcb_insight path/to/board.kicad_pcb

# Generate HTML report and CSV exports in specified output directory
python -m pcb_insight path/to/board.kicad_pcb --output-dir ./reports/ --html --csv
```

---

## 3. Verification & Diagnostic Checks

To verify your installation:

```bash
# Verify unit and integration test suite
pytest tests/ -v

# Check kicad-cli DRC availability
kicad-cli pcb drc --help
```
