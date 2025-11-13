"""Workarounds für bekannte eppy Bugs.

Eppy ist ein exzellentes Tool für EnergyPlus IDF-Manipulation, hat aber
einige bekannte Bugs, insbesondere beim Speichern von inter-zone boundary objects.

Dieser Modul isoliert diese fragilen Workarounds und dokumentiert die Bugs.
"""

import re
from pathlib import Path
from typing import Any, Dict


class EppyBugFixer:
    """Sammlung von Workarounds für eppy Bugs.

    BEKANNTER BUG: eppy überschreibt Outside_Boundary_Condition_Object beim Save
    -

--------------------------------------------------------------------------

    Wenn ein BUILDINGSURFACE:DETAILED ein Outside_Boundary_Condition = "Surface" hat
    (d.h. es grenzt an eine andere Zone), sollte Outside_Boundary_Condition_Object
    den Namen der angrenzenden Surface enthalten.

    **BUG:** eppy setzt beim Save() fälschlicherweise Outside_Boundary_Condition_Object = Name
    (Self-Reference statt Referenz zur Nachbar-Surface).

    **WORKAROUND:** Vor dem Save() alle korrekten Boundary-Referenzen sammeln,
    nach dem Save() per Regex im gespeicherten File korrigieren.

    Siehe: https://github.com/santoshphilip/eppy/issues/XXX (falls Issue existiert)
    """

    def __init__(self, debug: bool = False):
        """
        Args:
            debug: Wenn True, werden Debug-Ausgaben angezeigt
        """
        self.debug = debug

    def collect_boundary_map(self, idf: Any) -> Dict[str, str]:
        """Sammelt Boundary Objects VOR dem eppy Save.

        Diese Methode MUSS vor idf.save() aufgerufen werden, da save()
        die Boundary Objects korrupt (siehe Bug-Beschreibung oben).

        Args:
            idf: eppy IDF-Objekt

        Returns:
            Dictionary: {surface_name: correct_boundary_object_name}

        Example:
            >>> boundary_map = fixer.collect_boundary_map(idf)
            >>> idf.save("building.idf")
            >>> fixer.fix_eppy_boundary_objects(boundary_map, Path("building.idf"))
        """
        boundary_map = {}

        for surf in idf.idfobjects["BUILDINGSURFACE:DETAILED"]:
            if surf.Outside_Boundary_Condition == "Surface":
                boundary_obj = surf.Outside_Boundary_Condition_Object
                boundary_map[surf.Name] = boundary_obj

                # Debug output für spezifische Surfaces
                if self.debug:
                    if any(name in surf.Name for name in [
                        "Perimeter_North_F1_Wall_To_Core",
                        "Core_F1_Wall_To_North"
                    ]):
                        print(f"  DEBUG boundary_map: {surf.Name} → {boundary_obj}")

        return boundary_map

    def fix_eppy_boundary_objects(
        self,
        boundary_map: Dict[str, str],
        output_path: Path
    ) -> int:
        """Korrigiert eppy Bug in gespeicherter IDF-Datei.

        Diese Methode MUSS nach idf.save() aufgerufen werden.
        Sie liest die gespeicherte Datei, korrigiert die falschen Boundary-Referenzen
        und schreibt die korrigierte Version zurück.

        Args:
            boundary_map: Pre-collected boundary objects (von collect_boundary_map())
            output_path: Pfad zur gespeicherten IDF-Datei

        Returns:
            Anzahl korrigierter Boundary-Referenzen

        Algorithm:
            Für jede Surface mit falscher Boundary-Referenz:
            1. Finde den BUILDINGSURFACE:DETAILED-Block für diese Surface
            2. Lokalisiere die Zeile "Outside Boundary Condition Object"
            3. Ersetze den falschen Wert mit dem korrekten aus boundary_map
            4. Wichtig: NUR innerhalb dieses Blocks ersetzen (nicht global!)
        """
        # 1. Lese gespeicherte IDF-Datei
        with open(output_path, 'r', encoding='utf-8') as f:
            idf_content = f.read()

        original_size = len(idf_content)
        corrections = 0

        # 2. Korrigiere jede falsche Self-Reference
        for surf_name, correct_boundary in boundary_map.items():
            # Pattern: Finde den BUILDINGSURFACE:DETAILED Block für diese Surface
            # und ersetze NUR die Boundary Object Zeile IN DIESEM Block
            #
            # Format:
            # BUILDINGSURFACE:DETAILED,
            #     SurfaceName,    !- Name
            #     Wall,           !- Surface Type
            #     ...
            #     Surface,        !- Outside Boundary Condition
            #     <WRONG_VALUE>,  !- Outside Boundary Condition Object  <- DIESE Zeile!

            pattern = (
                rf'(BUILDINGSURFACE:DETAILED,\s+'  # Start of block
                rf'{re.escape(surf_name)},\s+!- Name\s+'  # This surface's name
                rf'.*?'  # Any lines in between (non-greedy)
                rf'Surface,\s+!- Outside Boundary Condition\s+'  # "Surface" boundary
                rf')(\S+)(,\s+!- Outside Boundary Condition Object)'  # Old value
            )

            # Replacement: Keep prefix, replace value, keep suffix
            replacement = rf'\1{correct_boundary}\3'

            new_content, count = re.subn(
                pattern,
                replacement,
                idf_content,
                flags=re.DOTALL
            )

            if count > 0:
                idf_content = new_content
                corrections += count

                if self.debug:
                    print(
                        f"  DEBUG fixed: {surf_name[:40]:40} → "
                        f"{correct_boundary[:40]:40} (blocks={count})"
                    )

        # 3. Schreibe korrigiertes IDF zurück (nur wenn Änderungen)
        if corrections > 0:
            if self.debug:
                print(f"  DEBUG: Writing corrected IDF to {output_path}")
                print(f"  DEBUG: File size before: {original_size} bytes")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(idf_content)

            new_size = Path(output_path).stat().st_size

            if self.debug:
                print(f"  DEBUG: File size after: {new_size} bytes")
                self._verify_fix(output_path)

            print(f"  🔧 Fixed {corrections} eppy boundary object bugs")
        else:
            if self.debug:
                print("  No eppy boundary object bugs found (unexpected!)")

        return corrections

    def _verify_fix(self, output_path: Path) -> None:
        """Verifiziert dass der Fix tatsächlich geschrieben wurde (Debug).

        Args:
            output_path: Pfad zur korrigierten IDF-Datei
        """
        with open(output_path, 'r', encoding='utf-8') as f:
            verify_content = f.read()

        # Simple string search für spezifische korrigierte Werte
        if "Core_F1_Wall_To_North," in verify_content:
            print("  ✅ VERIFY: Found 'Core_F1_Wall_To_North' in file")
        else:
            print("  ❌ VERIFY: 'Core_F1_Wall_To_North' NOT found in file!")

        # Check was tatsächlich in den Boundary Object Zeilen steht
        blocks = re.findall(
            r'(^\s+\S+,\s+!- Name\n(?:.*\n){5}^\s+Surface,\s+!- Outside Boundary Condition\n'
            r'^\s+(\S+),\s+!- Outside Boundary Condition Object)',
            verify_content,
            flags=re.MULTILINE
        )

        print(f"  DEBUG VERIFY: Found {len(blocks)} surface-type blocks")
        for i, (block, boundary) in enumerate(blocks[:3]):  # Zeige max 3
            print(f"    Block {i+1} boundary: {boundary}")
