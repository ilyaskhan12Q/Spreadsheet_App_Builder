import xml.etree.ElementTree as ET
from pathlib import Path

BASIC_MACRO_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="SAB_Helper" script:language="StarBasic">
REM  ##### SpreadsheetAppBuilder Helpers #####

Sub run_sab_action(actionName As String)
    MsgBox "Triggered SpreadsheetAppBuilder action: " & actionName
End Sub
</script:module>
"""


def install_sab_macros() -> None:
    """
    Copies the SAB Basic macro helper into the LibreOffice user profile
    and registers it in the 'Standard' Basic library.
    """
    home = Path.home()

    # Standard LibreOffice user profile path for Linux
    lo_profile = home / ".config" / "libreoffice" / "4" / "user"

    # Check if LibreOffice profile directory exists. If not, print fallback warning.
    if not lo_profile.exists():
        # Try finding any folder matching libreoffice in config
        lo_candidates = list((home / ".config").glob("libreoffice*"))
        if lo_candidates:
            lo_profile = lo_candidates[0] / "4" / "user"
        else:
            print(f"LibreOffice profile not found at {lo_profile}. Please ensure LibreOffice is installed.")
            return

    basic_dir = lo_profile / "basic"
    standard_lib = basic_dir / "Standard"
    standard_lib.mkdir(parents=True, exist_ok=True)

    # 1. Write the SAB_Helper.xba file
    xba_file = standard_lib / "SAB_Helper.xba"
    xba_file.write_text(BASIC_MACRO_CONTENT, encoding="utf-8")
    print(f"Created macro module at: {xba_file}")

    # 2. Register module in script.xlb
    xlb_file = standard_lib / "script.xlb"

    if xlb_file.exists():
        # Update existing script.xlb
        try:
            tree = ET.parse(xlb_file)
            root = tree.getroot()

            # Check if SAB_Helper already registered
            elements = [elem.get("{http://openoffice.org/2000/script}element") for elem in root.findall(".//{http://openoffice.org/2000/script}library-index")]
            # Handle elements without namespaces
            elements_no_ns = [elem.get("element") for elem in root.findall(".//library-index")]
            all_elements = set(elements + elements_no_ns)

            if "SAB_Helper" not in all_elements:
                # Add child element
                ns = "http://openoffice.org/2000/script"
                ET.register_namespace('script', ns)
                new_elem = ET.Element(f"{{{ns}}}library-index", {"{http://openoffice.org/2000/script}element": "SAB_Helper"})
                root.append(new_elem)
                tree.write(xlb_file, xml_declaration=True, encoding="utf-8")
                print("Registered SAB_Helper in existing script.xlb.")
            else:
                print("SAB_Helper is already registered in script.xlb.")
        except Exception as e:
            print(f"Error parsing script.xlb: {e}. Overwriting with default structure.")
            create_default_xlb(xlb_file)
    else:
        # Create new script.xlb
        create_default_xlb(xlb_file)


def create_default_xlb(xlb_path: Path) -> None:
    ns = "http://openoffice.org/2000/script"
    ET.register_namespace('script', ns)

    root = ET.Element(f"{{{ns}}}library-document", {
        f"{{{ns}}}name": "Standard",
        f"{{{ns}}}readonly": "false",
        f"{{{ns}}}passwordporting": "false"
    })

    elem = ET.Element(f"{{{ns}}}library-index", {
        f"{{{ns}}}element": "SAB_Helper"
    })
    root.append(elem)

    tree = ET.ElementTree(root)
    tree.write(xlb_path, xml_declaration=True, encoding="utf-8")
    print(f"Created and registered SAB_Helper in new script.xlb at: {xlb_path}")


if __name__ == "__main__":
    install_sab_macros()
