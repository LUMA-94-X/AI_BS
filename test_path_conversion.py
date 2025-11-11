#!/usr/bin/env python3
"""Test bidirectional path conversion for WSL/Windows hybrid environment."""

import os
import platform
from pathlib import Path

def test_path_conversion():
    """Test path conversion logic."""

    print("=" * 80)
    print("PATH CONVERSION TEST")
    print("=" * 80)

    # Detect environment
    system = platform.system()
    cwd = os.getcwd()

    is_wsl = False
    if system == "Linux":
        try:
            with open('/proc/version', 'r') as f:
                is_wsl = 'microsoft' in f.read().lower()
        except:
            pass

    running_in_wsl_alt = cwd.startswith("/mnt/") or (platform.system() == "Linux" and os.path.exists("/mnt/c"))

    print(f"\nEnvironment Detection:")
    print(f"  Platform: {system}")
    print(f"  Working directory: {cwd}")
    print(f"  Is WSL (method 1 - /proc/version): {is_wsl}")
    print(f"  Is WSL (method 2 - cwd check): {running_in_wsl_alt}")

    # Test cases
    test_paths = [
        "/mnt/c/EnergyPlusV25-1-0",
        "C:/EnergyPlusV25-1-0",
        "C:\\EnergyPlusV25-1-0",
        "/mnt/d/SomeFolder",
    ]

    print(f"\n{'Original Path':<35} | {'Converted Path':<35} | Method")
    print("-" * 80)

    for original_path in test_paths:
        ep_path_str = original_path

        # Conversion logic (same as in five_zone_generator.py)
        if is_wsl or running_in_wsl_alt:
            # Running in WSL: Convert C:/ to /mnt/c/
            if ep_path_str.startswith("C:/") or ep_path_str.startswith("C:\\"):
                ep_path_str = ep_path_str.replace("C:/", "/mnt/c/").replace("C:\\", "/mnt/c/").replace("\\", "/")
                method = "WSL: C: → /mnt/c/"
            else:
                method = "WSL: No conversion"
        else:
            # Running in Windows: Convert /mnt/c/ to C:/
            if ep_path_str.startswith("/mnt/c/"):
                ep_path_str = ep_path_str.replace("/mnt/c/", "C:/")
                method = "Windows: /mnt/c/ → C:/"
            elif ep_path_str.startswith("/mnt/"):
                # Other drives: /mnt/d/ -> D:/
                parts = ep_path_str[5:].split("/", 1)
                if len(parts) >= 1:
                    drive = parts[0].upper()
                    rest = parts[1] if len(parts) > 1 else ""
                    ep_path_str = f"{drive}:/{rest}"
                    method = f"Windows: /mnt/{drive.lower()}/ → {drive}:/"
            else:
                method = "Windows: No conversion"

        print(f"{original_path:<35} | {ep_path_str:<35} | {method}")

    # Test actual paths
    print("\n" + "=" * 80)
    print("ACTUAL PATH TESTS")
    print("=" * 80)

    # Test config path conversion
    from core.config import get_config

    config = get_config()
    print(f"\nConfig installation_path: {config.energyplus.installation_path}")

    try:
        exe_path = config.energyplus.get_executable_path()
        print(f"Executable path: {exe_path}")
        print(f"Executable exists: {exe_path.exists()}")
    except Exception as e:
        print(f"❌ Error getting executable path: {e}")

    # Test IDD path (used by FiveZoneGenerator)
    print(f"\nTesting IDD path resolution:")
    ep_path_str = config.energyplus.installation_path

    if is_wsl or running_in_wsl_alt:
        if ep_path_str.startswith("C:/") or ep_path_str.startswith("C:\\"):
            ep_path_str = ep_path_str.replace("C:/", "/mnt/c/").replace("C:\\", "/mnt/c/").replace("\\", "/")
    else:
        if ep_path_str.startswith("/mnt/c/"):
            ep_path_str = ep_path_str.replace("/mnt/c/", "C:/")
        elif ep_path_str.startswith("/mnt/"):
            parts = ep_path_str[5:].split("/", 1)
            if len(parts) >= 1:
                drive = parts[0].upper()
                rest = parts[1] if len(parts) > 1 else ""
                ep_path_str = f"{drive}:/{rest}"

    idd_path = Path(ep_path_str) / "Energy+.idd"
    print(f"  Original config path: {config.energyplus.installation_path}")
    print(f"  Converted path: {ep_path_str}")
    print(f"  IDD path: {idd_path}")
    print(f"  IDD exists: {idd_path.exists()}")

    if idd_path.exists():
        print(f"\n✅ SUCCESS: IDD file found!")
    else:
        print(f"\n❌ FAILED: IDD file not found at {idd_path}")
        print(f"   Check EnergyPlus installation at this path")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    test_path_conversion()
