from __future__ import annotations

import contextlib
import io
from pathlib import Path

from AoE2ScenarioParser.objects.data_objects.condition import Condition
from AoE2ScenarioParser.objects.data_objects.effect import Effect
from AoE2ScenarioParser.objects.data_objects.trigger import Trigger
from AoE2ScenarioParser.objects.managers.unit_manager import create_id_generator
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
from AoE2ScenarioParser.sections.aoe2_file_section import AoE2FileSection

from .models import LegacyCondition, LegacyEffect, LegacyScenario

MESSAGE_FIELDS = ("instructions", "hints", "victory", "loss", "history", "scouts")
VICTORY_FIELDS = (
    "conquest_required",
    "ruins",
    "artifacts_required",
    "discovery",
    "explored_percent_of_map_required",
    "gold_required",
    "all_custom_conditions_required",
    "mode",
    "required_score_for_score_victory",
    "time_for_timed_game_in_10ths_of_a_year",
)


def latest_target_version() -> str:
    return ".".join(str(part) for part in AoE2DEScenario.LATEST_VERSION)


def _field(values: list[int], index: int, default: int = -1) -> int:
    return values[index] if index < len(values) else default


def _effect(old: LegacyEffect, uuid) -> Effect:
    fields = old.fields
    converted = Effect(
        effect_type=old.effect_type,
        ai_script_goal=_field(fields, 0),
        _quantity_int=_field(fields, 1),
        tribute_list=_field(fields, 2),
        diplomacy=_field(fields, 3),
        legacy_location_object_reference=_field(fields, 5),
        location_object_reference=_field(fields, 5),
        object_list_unit_id=_field(fields, 6),
        object_list_unit_id_2=-1,
        source_player=_field(fields, 7),
        target_player=_field(fields, 8),
        technology=_field(fields, 9),
        string_id=_field(fields, 10),
        display_time=_field(fields, 12),
        trigger_id=_field(fields, 13),
        location_x=_field(fields, 15),
        location_y=_field(fields, 14),
        area_x1=_field(fields, 17),
        area_y1=_field(fields, 16),
        area_x2=_field(fields, 19),
        area_y2=_field(fields, 18),
        object_group=_field(fields, 20),
        object_type=_field(fields, 21),
        instruction_panel_position=_field(fields, 22),
        attack_stance=_field(fields, 23),
        message=old.message,
        sound_name=old.sound_name,
        selected_object_ids=list(old.selected_object_ids),
        uuid=uuid,
    )
    integer_defaults = (
        "time_unit", "enabled", "food", "wood", "stone", "gold", "flash_object",
        "force_research_technology", "visibility_state", "scroll", "operation",
        "button_location", "ai_signal_value", "object_attributes", "variable", "timer",
        "facet", "play_sound", "player_color", "color_mood", "reset_timer", "object_state",
        "action_type", "resource_1", "resource_1_quantity", "resource_2",
        "resource_2_quantity", "resource_3", "resource_3_quantity", "decision_id",
        "string_id_option1", "string_id_option2", "variable2", "max_units_affected",
        "disable_garrison_unload_sound", "hotkey", "train_time", "local_technology",
        "disable_sound", "object_group2", "object_type2", "facet2", "global_sound",
        "issue_group_command", "queue_action", "mutual_diplomacy", "building_list",
        "wall_x1", "wall_y1", "wall_x2", "wall_y2", "object_filter",
    )
    for attribute in integer_defaults:
        if getattr(converted, attribute, None) is None:
            setattr(converted, attribute, -1)
    converted._item_id = -1
    converted.use_tag_color_for_icon = False
    converted.message_option1 = ""
    converted.message_option2 = ""
    return converted


def _condition(old: LegacyCondition, uuid) -> Condition:
    fields = old.fields
    converted = Condition(
        condition_type=old.condition_type,
        quantity=_field(fields, 0),
        attribute=_field(fields, 1),
        unit_object=_field(fields, 2),
        next_object=_field(fields, 3),
        object_list=_field(fields, 4),
        source_player=_field(fields, 5),
        technology=_field(fields, 6),
        timer=_field(fields, 7),
        trigger_id=_field(fields, 8),
        area_x1=_field(fields, 10),
        area_y1=_field(fields, 9),
        area_x2=_field(fields, 12),
        area_y2=_field(fields, 11),
        object_group=_field(fields, 13),
        object_type=_field(fields, 14),
        ai_signal=_field(fields, 15),
        inverted=_field(fields, 16),
        uuid=uuid,
    )
    for attribute in (
        "variable", "comparison", "target_player", "unit_ai_action", "object_state",
        "timer_id", "victory_timer_type", "include_changeable_weapon_objects",
        "decision_id", "decision_option", "variable2", "local_technology",
        "object_group2", "object_type2",
    ):
        if getattr(converted, attribute, None) is None:
            setattr(converted, attribute, -1)
    converted.xs_function = ""
    return converted


def _decode_script(payload: bytes) -> str:
    return payload.rstrip(b"\0").decode("cp1252", errors="replace")


def _struct(section, name: str):
    return AoE2FileSection.from_model(section.struct_models[name], uuid=section._uuid, set_defaults=False)


def _populate_files(target: AoE2DEScenario, source: LegacyScenario) -> None:
    files_section = target.sections["Files"]
    preserved: list[tuple[str, bytes]] = list(source.included_files)
    for player in source.players:
        for kind in ("vc", "cty"):
            payload = player.embedded_ai.get(kind)
            if not payload:
                continue
            name = player.ai_names.get(kind) or f"player_{player.legacy_index + 1}.{kind}"
            preserved.append((name, payload))
    deduplicated: dict[str, bytes] = {}
    for name, payload in preserved:
        deduplicated.setdefault(name or "included_file", payload)
    structs = []
    for name, payload in deduplicated.items():
        item = _struct(files_section, "AI2Struct")
        item.ai_file_name = name
        item.ai_file = _decode_script(payload)
        structs.append(item)
    files_section.ai_files = structs
    files_section.number_of_ai_files = len(structs)
    files_section.ai_files_present = int(bool(structs))


def build_de_scenario(source: LegacyScenario) -> AoE2DEScenario:
    with contextlib.redirect_stdout(io.StringIO()):
        target = AoE2DEScenario.from_default()

    target.sections["FileHeader"].creator_name = "AoE2 Scenario Migrator"
    target.sections["DataHeader"].filename = source.original_filename
    target.sections["DataHeader"].next_unit_id_to_place = source.next_uid

    for index, field in enumerate(MESSAGE_FIELDS):
        if index >= len(source.messages):
            continue
        setattr(target.message_manager, field, source.messages[index])
        setattr(
            target.message_manager,
            f"{field}_string_table_id",
            source.message_string_ids[index] & 0xFFFFFFFF,
        )
    cinematic_section = target.sections["Cinematics"]
    cinematic_section.ascii_pregame = source.cinematics[0]
    cinematic_section.ascii_victory = source.cinematics[1]
    cinematic_section.ascii_loss = source.cinematics[2]
    target.sections["BackgroundImage"].ascii_filename = source.cinematics[3]

    for old_index in range(9):
        old_player = source.players[old_index]
        de_index = 0 if old_index == 8 else old_index + 1
        player = target.player_manager.players[de_index]
        player._active = bool(old_player.enabled)
        player.human = bool(old_player.human)
        player.civilization = old_player.civilization
        player.architecture_set = old_player.civilization
        player.food = int(old_player.resources[2])
        player.wood = int(old_player.resources[1])
        player.gold = int(old_player.resources[0])
        player.stone = int(old_player.resources[3])
        player.color = old_player.color
        player.starting_age = max(2, min(6, old_player.starting_age + 2))
        if de_index:
            player.population_cap = old_player.population_limit
            player.diplomacy = list(old_player.diplomacy[:16])
            player.allied_victory = bool(old_player.allied_victory)
            player.disabled_techs = list(old_player.disabled_techs)
            player.disabled_units = list(old_player.disabled_units)
            player.disabled_buildings = list(old_player.disabled_buildings)
            player.tribe_name = old_player.name
            player.string_table_name_id = old_player.string_table_name_id
            player._initial_camera_x = round(old_player.camera_x)
            player._initial_camera_y = round(old_player.camera_y)
            player.initial_player_view_x = round(old_player.camera_x)
            player.initial_player_view_y = round(old_player.camera_y)

    target.option_manager.lock_teams = bool(source.lock_teams)
    target.option_manager.allow_players_choose_teams = bool(source.allow_players_choose_teams)
    target.option_manager.random_start_points = bool(source.random_start_points)
    target.sections["Diplomacy"].max_number_of_teams = max(1, min(8, source.max_teams))
    target.sections["Options"].all_techs = source.all_techs
    target.sections["Options"].ai_map_type = source.map_ai_type
    victory_section = target.sections["GlobalVictory"]
    for field, value in zip(VICTORY_FIELDS, source.victory):
        setattr(victory_section, field, value)

    player_data_two = target.sections["PlayerDataTwo"]
    player_data_two.strings = [p.ai_names.get("vc", "") for p in source.players]
    player_data_two.strings += [p.ai_names.get("cty", "") for p in source.players]
    player_data_two.ai_names = [p.ai_names.get("ai", "") for p in source.players]
    player_data_two.ai_type = [p.ai_mode for p in source.players]
    ai_structs = []
    for player in source.players:
        item = _struct(player_data_two, "AIStruct")
        item.unknown = b"\0" * 8
        item.ai_per_file_text = _decode_script(player.embedded_ai.get("ai", b""))
        ai_structs.append(item)
    player_data_two.ai_files = ai_structs

    target.map_manager.map_size = source.map_width
    classic_terrain = source.inner_version in {"1.18", "1.19", "1.20", "1.21", "1.22"}
    for x in range(source.map_width):
        for y in range(source.map_height):
            terrain_id, elevation = source.terrain[x * source.map_height + y]
            if classic_terrain and terrain_id == 41:
                terrain_id = 47
            tile = target.map_manager.get_tile(x, y)
            tile.terrain_id = terrain_id
            tile.elevation = max(0, min(8, elevation))
            tile.layer = -1

    target.unit_manager.units = [[] for _ in range(9)]
    for unit in source.units:
        owner = 0 if unit.owner_block == 8 else unit.owner_block + 1
        garrison = unit.garrisoned_in_id
        if source.format_name == "Age of Kings" and garrison == 0:
            garrison = -1
        target.unit_manager.add_unit(
            player=owner,
            unit_const=unit.unit_const,
            x=unit.x,
            y=unit.y,
            z=unit.z,
            rotation=unit.rotation,
            garrisoned_in_id=garrison,
            animation_frame=unit.animation_frame,
            status=unit.status,
            reference_id=unit.reference_id,
        )
    target.unit_manager.reference_id_generator = create_id_generator(max(
        source.next_uid,
        max((unit.reference_id for unit in source.units), default=-1) + 1,
    ))

    converted_triggers = []
    for trigger_id, old in enumerate(source.triggers):
        effects = [_effect(effect, target.uuid) for effect in old.effects]
        conditions = [_condition(condition, target.uuid) for condition in old.conditions]
        converted_triggers.append(
            Trigger(
                name=old.name,
                description=old.description,
                description_stid=old.objective_string_id,
                display_as_objective=old.objective,
                description_order=old.objective_order,
                enabled=old.enabled,
                looping=old.looping,
                effects=effects,
                effect_order=list(old.effect_order),
                conditions=conditions,
                condition_order=list(old.condition_order),
                trigger_id=trigger_id,
                uuid=target.uuid,
            )
        )
    target.trigger_manager.triggers = converted_triggers
    target.trigger_manager.trigger_display_order = list(source.trigger_order)
    target.option_manager.legacy_execution_order = True
    _populate_files(target, source)
    return target


def write_de_scenario(target: AoE2DEScenario, path: Path) -> None:
    with contextlib.redirect_stdout(io.StringIO()):
        target.write_to_file(str(path))
