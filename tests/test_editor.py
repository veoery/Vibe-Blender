"""Unit tests for the edit application engine (editor.py).

No LLM or Blender dependency — pure logic tests covering all four matchers,
sequential application, rollback on failure, and edge cases.
"""

import pytest

from vibe_blender.agents.editor import apply_edits, locate_edit, EditResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_SCRIPT = """\
import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Add cube
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "MyCube"

# Material
mat = bpy.data.materials.new(name="CubeMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Metallic"].default_value = 0.1
bsdf.inputs["Roughness"].default_value = 0.5
obj.data.materials.append(mat)

# Save
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
"""


# ---------------------------------------------------------------------------
# ExactReplacer — single occurrence (success)
# ---------------------------------------------------------------------------


class TestExactMatch:
    def test_single_occurrence_success(self):
        edits = [{"old_code": 'obj.name = "MyCube"', "new_code": 'obj.name = "Box"'}]
        result = apply_edits(SAMPLE_SCRIPT, edits)
        assert result.success
        assert 'obj.name = "Box"' in result.code
        assert 'obj.name = "MyCube"' not in result.code
        assert result.applied_count == 1

    def test_multiple_occurrences_raises(self):
        # "bpy" appears many times — locate_edit should raise ValueError
        with pytest.raises(ValueError, match="multiple times"):
            locate_edit(SAMPLE_SCRIPT, "bpy")

    def test_zero_occurrences_returns_none(self):
        result = locate_edit(SAMPLE_SCRIPT, "THIS_STRING_DOES_NOT_EXIST_ANYWHERE")
        assert result is None


# ---------------------------------------------------------------------------
# LineTrimmedReplacer — trailing whitespace drift
# ---------------------------------------------------------------------------


class TestLineTrimmedMatch:
    def test_old_code_has_trailing_spaces(self):
        # old_code has trailing spaces the actual script does not
        old = 'bsdf.inputs["Metallic"].default_value = 0.1   '
        edits = [{"old_code": old, "new_code": 'bsdf.inputs["Metallic"].default_value = 0.8'}]
        result = apply_edits(SAMPLE_SCRIPT, edits)
        assert result.success
        assert "0.8" in result.code
        assert result.applied_count == 1

    def test_script_has_trailing_spaces(self):
        # Inject trailing spaces into the script; old_code is clean
        script_with_spaces = SAMPLE_SCRIPT.replace(
            'bsdf.inputs["Roughness"].default_value = 0.5',
            'bsdf.inputs["Roughness"].default_value = 0.5   ',
        )
        old = 'bsdf.inputs["Roughness"].default_value = 0.5'
        edits = [{"old_code": old, "new_code": 'bsdf.inputs["Roughness"].default_value = 0.3'}]
        result = apply_edits(script_with_spaces, edits)
        assert result.success
        assert "0.3" in result.code


# ---------------------------------------------------------------------------
# IndentationFlexibleReplacer — indent drift
# ---------------------------------------------------------------------------


class TestIndentationFlexibleMatch:
    def test_old_at_indent_0_actual_at_indent_4(self):
        # Script has a block indented at 4; old_code quotes it at indent 0
        script = (
            "def setup():\n"
            "    mat = bpy.data.materials.new(name=\"M\")\n"
            "    mat.use_nodes = True\n"
            "    bsdf = mat.node_tree.nodes.get(\"Principled BSDF\")\n"
        )
        old_code = (
            "mat = bpy.data.materials.new(name=\"M\")\n"
            "mat.use_nodes = True\n"
            "bsdf = mat.node_tree.nodes.get(\"Principled BSDF\")"
        )
        new_code = (
            "mat = bpy.data.materials.new(name=\"M\")\n"
            "mat.use_nodes = True\n"
            "bsdf = mat.node_tree.nodes.get(\"Principled BSDF\")\n"
            "bsdf.inputs[\"Metallic\"].default_value = 0.9"
        )
        # The editor will re-indent old_code to 4 spaces to match the script
        edits = [{"old_code": old_code, "new_code": new_code}]
        result = apply_edits(script, edits)
        assert result.success
        # The new_code gets inserted at indent 0; that's fine for this test —
        # the key assertion is that the match was found despite indent mismatch
        assert "Metallic" in result.code

    def test_old_at_indent_4_actual_at_indent_0(self):
        script = (
            "mat = bpy.data.materials.new(name=\"M\")\n"
            "mat.use_nodes = True\n"
        )
        old_code = (
            "    mat = bpy.data.materials.new(name=\"M\")\n"
            "    mat.use_nodes = True"
        )
        new_code = "    mat = bpy.data.materials.new(name=\"NewMat\")\n    mat.use_nodes = True"
        edits = [{"old_code": old_code, "new_code": new_code}]
        result = apply_edits(script, edits)
        assert result.success
        assert "NewMat" in result.code


# ---------------------------------------------------------------------------
# BlankLineFlexibleReplacer — blank line insertion/removal
# ---------------------------------------------------------------------------


class TestBlankLineFlexibleMatch:
    def test_extra_blank_line_in_script(self):
        # Script has an extra blank line between two statements; old_code does not
        script = (
            "obj.name = \"Box\"\n"
            "\n"
            "\n"
            "obj.location = (1, 0, 0)\n"
        )
        old_code = "obj.name = \"Box\"\n\nobj.location = (1, 0, 0)"
        new_code = "obj.name = \"Box\"\n\nobj.location = (2, 0, 0)"
        edits = [{"old_code": old_code, "new_code": new_code}]
        result = apply_edits(script, edits)
        assert result.success
        assert "(2, 0, 0)" in result.code

    def test_missing_blank_line_in_script(self):
        # Script has no blank line; old_code has one
        script = "obj.name = \"Box\"\nobj.location = (1, 0, 0)\n"
        old_code = "obj.name = \"Box\"\n\nobj.location = (1, 0, 0)"
        new_code = "obj.name = \"Box\"\nobj.location = (3, 0, 0)"
        edits = [{"old_code": old_code, "new_code": new_code}]
        result = apply_edits(script, edits)
        assert result.success
        assert "(3, 0, 0)" in result.code


# ---------------------------------------------------------------------------
# Sequential application
# ---------------------------------------------------------------------------


class TestSequentialEdits:
    def test_edit2_target_created_by_edit1(self):
        script = 'color = "red"\n'
        edits = [
            {"old_code": 'color = "red"', "new_code": 'color = "blue"\nsize = 5'},
            {"old_code": "size = 5", "new_code": "size = 10"},
        ]
        result = apply_edits(script, edits)
        assert result.success
        assert "size = 10" in result.code
        assert result.applied_count == 2

    def test_sequential_failure_returns_original(self):
        # Edit 1 succeeds, edit 2 targets something that doesn't exist
        script = 'color = "red"\nsize = 5\n'
        edits = [
            {"old_code": 'color = "red"', "new_code": 'color = "blue"'},
            {"old_code": "NONEXISTENT_TARGET", "new_code": "whatever"},
        ]
        result = apply_edits(script, edits)
        assert not result.success
        # Original code is returned unchanged
        assert result.code == script
        assert result.applied_count == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_edits_list_is_noop(self):
        result = apply_edits(SAMPLE_SCRIPT, [])
        assert result.success
        assert result.code == SAMPLE_SCRIPT
        assert result.applied_count == 0

    def test_new_code_empty_deletes_target(self):
        edits = [{"old_code": '# Add cube\n', "new_code": ""}]
        result = apply_edits(SAMPLE_SCRIPT, edits)
        assert result.success
        assert "# Add cube" not in result.code

    def test_old_code_empty_returns_failure(self):
        edits = [{"old_code": "", "new_code": "something"}]
        result = apply_edits(SAMPLE_SCRIPT, edits)
        assert not result.success
        assert result.error is not None
        assert "empty" in result.error.lower()
