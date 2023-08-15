"""
Contains the functions used by the Water Quality Control tool 
tool and other helper functions.
"""

import re

import arcpy

import colawater.attribute as attr
import colawater.status.logging as log
import colawater.status.progressor as pg
import colawater.status.summary as sy
from colawater.tools.checks import fids, mains

_LAYER_START = 4


def execute(parameters: list[arcpy.Parameter]) -> None:
    """
    Entry point for Water Quality Control.
    """
    pg.set_progressor("default", "Starting quality control checks...")

    is_checks = parameters[:_LAYER_START]
    layers = parameters[_LAYER_START:]
    wm_layer = layers[-1]
    is_fid_format_check = is_checks[0].value
    is_fid_duplicate_check = is_checks[1].value
    is_wm_file_check = is_checks[2].value
    is_wm_ds_check = is_checks[3].value

    for l in (l for l in layers if not l.value):
        log.warning(f"Layer omitted: {l.displayName}")

    if is_fid_format_check:
        pg.set_progressor("step", "Checking facility identifier formatting...", 0, 7)
        # regexes correspond 1:1 with layer parameters
        regexes = (
            r"^\d+CA$",
            r"^\d+CV$",
            r"^\d+FT$",
            r"^\d+HYD$",
            r"^\d+SERV$",
            r"^\d+STR$",
            r"^\d+SV$",
            r"^000015-WATER-000\d+$",
        )

        for l, r in zip(layers, regexes):
            if not l.value:
                pg.increment()
                continue

            log.info(f"[{l.valueAsText}] Checking facility identifier formatting...")

            inc_fids = fids.find_incorrect_fids(l, re.compile(r))

            pg.increment()
            sy.add_result(
                l.valueAsText,
                "Incorrectly formatted facility identifiers (object ID, facility identifier):",
            )
            if inc_fids:
                sy.add_note(l.valueAsText, attr.CSV_PROCESSING_MSG)
            sy.add_items(inc_fids, csv=True)
            sy.add_result(
                l.valueAsText,
                f"{len(inc_fids):n} incorrectly formatted facility identifiers.",
            )

    if is_fid_duplicate_check:
        pg.set_progressor(
            "step", "Checking for duplicate facility identifiers...", 0, 7
        )

        for l in layers:
            if not l.value:
                pg.increment()
                continue

            log.info(
                f"[{l.valueAsText}] Checking for duplicate facility identifiers..."
            )

            duplicate_fids = fids.find_duplicate_fids(l.value)

            pg.increment()
            sy.add_result(
                l.valueAsText,
                "Duplicate facility identifiers grouped on each line (fid, object IDs):",
            )
            sy.add_items(duplicate_fids)
            # len(i) - 1 because the fid itself is the first value in the list
            num_duplicate = sum(len(i) - 1 if len(i) > 0 else 0 for i in duplicate_fids)
            sy.add_result(
                l.valueAsText,
                f"{num_duplicate:n} duplicate facility identifiers.",
            )

    if (is_wm_file_check or is_wm_ds_check) and not wm_layer.value:
        log.warning(
            f"Layer omitted: {wm_layer.displayName}, skipping water main checks."
        )
        return

    pg.set_progressor("default")

    if is_wm_file_check:
        log.info(
            f"[{wm_layer.valueAsText}] Verifying assiociated files for integrated mains..."
        )

        nonexistent_files = mains.find_nonexistent_assoc_files(wm_layer)

        sy.add_result(
            wm_layer.valueAsText, "Nonexistent associated files (object ID, comments):"
        )
        if nonexistent_files:
            sy.add_note(wm_layer.valueAsText, attr.CSV_PROCESSING_MSG)
        sy.add_items(nonexistent_files, csv=True)
        sy.add_result(
            wm_layer.valueAsText,
            f"{len(nonexistent_files):n} nonexistent files for integrated mains.",
        )
        num_unique = len({list[1] for list in nonexistent_files})
        sy.add_result(
            wm_layer.valueAsText,
            f"{num_unique:n} unique nonexistent files files for integrated mains.",
        )

    if is_wm_ds_check:
        log.info(
            f"[{wm_layer.valueAsText}] Checking data sources for integrated mains..."
        )

        inc_datasources = mains.find_incorrect_datasources(wm_layer)

        sy.add_result(
            wm_layer.valueAsText,
            "Missing or unknown data sources (object ID, datasource):",
        )
        if inc_datasources:
            sy.add_note(wm_layer.valueAsText, attr.CSV_PROCESSING_MSG)
        sy.add_items(inc_datasources, csv=True)
        sy.add_result(
            wm_layer.valueAsText,
            f"{len(inc_datasources):n} missing or unknown data sources for integrated mains.",
        )

    # TODO: domain conformation

    sy.post()


def parameters() -> list[arcpy.Parameter]:
    """
    Returns the parameters for Water Quality Control.

    Parameters are 3 of type GPBoolean and 7 of type GPFeatureLayer.

    Returns:
        list[arcpy.Parameter]: The list of parameters.
    """
    check_templates = (
        # make sure to increment LAYER_START if adding a check here
        ("fid_check", "Check facility identifier format"),
        ("fid_duplicate_check", "Check for duplicate facility identifiers"),
        ("wm_file_check", "Check water main files"),
        ("wm_datasource_check", "Check water main data sources"),
    )

    checks = [
        arcpy.Parameter(
            displayName=name,
            name=abbrev,
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input",
        )
        for abbrev, name in check_templates
    ]

    lyr_templates = (
        ("ca_lyr", "Casing"),
        ("cv_lyr", "Control Valve"),
        ("ft_lyr", "Fitting"),
        ("hy_lyr", "Hydrant"),
        ("sl_lyr", "Service Line"),
        ("st_lyr", "Structure"),
        ("sv_lyr", "System Valve"),
        ("wm_lyr", "Water Main"),
    )

    lyrs = [
        arcpy.Parameter(
            displayName=name,
            name=abbrev,
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input",
        )
        for abbrev, name in lyr_templates
    ]

    return [*checks, *lyrs]
