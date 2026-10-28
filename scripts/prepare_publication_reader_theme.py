"""Derive a dark review theme without changing accepted typography or geometry.
SPDX-License-Identifier: Apache-2.0
"""
import copy


def prepare_dark_theme(accepted_light, reviewed_dark_palette):
    light = copy.deepcopy(accepted_light)
    dark = reviewed_dark_palette
    if len(light['dataColors']) != len(dark['dataColors']):
        raise ValueError('Palette roles differ; reconcile rather than cycle colours')
    colours = dict(zip(light['dataColors'], dark['dataColors']))
    colours.update({light['background']: dark['background'],
                    light['foreground']: dark['foreground'],
                    light['tableAccent']: dark['tableAccent']})

    def replace(value):
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(v) for v in value]
        return colours.get(value, value) if isinstance(value, str) else value

    result = replace(light)
    # Registered resources require the internal theme name to match its reference.
    result['name'] = dark.get('name', light.get('name', 'Dark review'))
    return result
