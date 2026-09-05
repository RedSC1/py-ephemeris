// Included inside ziwei_module.cpp's anonymous namespace.
using namespace taiyin::ziwei;

PlacementInput placement_input(const py::dict& d) {
    PlacementInput r;
    r.year_stem = d["year_stem"].cast<int32_t>();
    r.year_branch = d["year_branch"].cast<int32_t>();
    r.month = d["month"].cast<int32_t>();
    r.day = d["day"].cast<int32_t>();
    r.hour_branch = d["hour_branch"].cast<int32_t>();
    return r;
}
PlacementPatch placement_patch(const py::dict& d) {
    PlacementPatch r;
    const char* keys[] = {"year_stem", "year_branch", "month", "day", "hour_branch", "update_bureau"};
    int32_t* values[] = {&r.year_stem, &r.year_branch, &r.month, &r.day, &r.hour_branch, &r.update_bureau};
    for (int i = 0; i < 6; ++i) {
        py::object value = d.attr("get")(keys[i], py::none());
        if (!value.is_none()) *values[i] = value.cast<int32_t>();
    }
    return r;
}
py::dict input_dict(const PlacementInput& r) {
    py::dict d;
    d["year_stem"] = r.year_stem; d["year_branch"] = r.year_branch;
    d["month"] = r.month; d["day"] = r.day; d["hour_branch"] = r.hour_branch;
    return d;
}
py::dict patch_dict(const PlacementPatch& r) {
    py::dict d;
    d["year_stem"] = r.year_stem; d["year_branch"] = r.year_branch;
    d["month"] = r.month; d["day"] = r.day; d["hour_branch"] = r.hour_branch;
    d["update_bureau"] = r.update_bureau;
    return d;
}
py::list omitted_list(const std::vector<OmittedPlacement>& values) {
    py::list result;
    for (const auto& item : values) {
        py::dict d; d["star_id"] = item.star_id;
        std::vector<int> inputs;
        for (auto input : item.missing_inputs) inputs.push_back(static_cast<int>(input));
        d["missing_inputs"] = inputs; result.append(d);
    }
    return result;
}

class NativeCastingChart {
public:
    NativeCastingChart(ZiweiContext context, CastingChart value)
        : context_(std::move(context)), value_(std::move(value)) {}
    py::dict summary() const {
        const auto& p = value_.plate;
        const auto& original = value_.original_chart ? *value_.original_chart : value_;
        py::dict d;
        d["input"] = input_dict(p.input);
        d["original_input"] = input_dict(original.plate.input);
        d["overrides"] = patch_dict(value_.modification.overrides);
        d["index"] = value_.index == UINT32_MAX ? py::object(py::none()) : py::object(py::int_(value_.index));
        d["number"] = value_.number; d["method"] = static_cast<int>(value_.method);
        d["gender"] = static_cast<int>(p.gender);
        d["chart_mode"] = static_cast<int>(value_.chart_mode);
        d["bureau"] = static_cast<int>(p.anchors.bureau);
        d["original_bureau"] = static_cast<int>(original.plate.anchors.bureau);
        d["body_palace"] = static_cast<int>(p.anchors.body_palace);
        d["ziwei"] = static_cast<int>(p.anchors.ziwei);
        d["tianfu"] = static_cast<int>(p.anchors.tianfu);
        d["life_master"] = p.life_master; d["body_master"] = p.body_master;
        d["year_transform_stem"] = static_cast<int>(p.year_transform_stem);
        d["transforms"] = transform_to_dict(p.year_transformations);
        d["update_bureau"] = value_.modification.update_bureau;
        d["life_palace_shift"] = value_.modification.life_palace_shift;
        std::vector<int> branches, stems;
        for (auto v : p.anchors.palace_positions) branches.push_back(static_cast<int>(v));
        for (auto v : p.anchors.palace_stems) stems.push_back(static_cast<int>(v));
        d["palace_branches"] = branches; d["palace_stems"] = stems;
        return d;
    }
    py::list omitted_placements() const { return omitted_list(value_.plate.omitted_placements); }
    int star_position(uint16_t id) const {
        const auto& positions = value_.plate.star_positions;
        return id >= positions.size() || positions[id] == 0xffu ? -1 : positions[id];
    }
    int star_palace(uint16_t id) const {
        const int branch = star_position(id);
        for (int i = 0; i < 12; ++i)
            if (static_cast<int>(value_.plate.anchors.palace_positions[i]) == branch) return i;
        return -1;
    }
    int brightness(uint16_t id) const {
        const int branch = star_position(id);
        if (branch < 0) return -1;
        Brightness out;
        require_ok(brightness_at(context_.compiled_tables(), id, static_cast<Branch>(branch), &out), "CastingChart.brightness");
        return static_cast<int>(out);
    }
    int transform_mask(uint16_t id) const {
        return id < value_.plate.transformation_masks.size() ? value_.plate.transformation_masks[id] : 0;
    }
    std::vector<uint16_t> palace_stars(int branch) const {
        if (branch < 0 || branch > 11) throw py::value_error("branch must be 0..11");
        std::vector<uint16_t> ids;
        const auto& bits = value_.plate.palaces[branch].stars;
        for (size_t i = 0; i < bits.size(); ++i) if (bits.test(i)) ids.push_back(static_cast<uint16_t>(i));
        return ids;
    }
    std::unique_ptr<NativeCastingChart> modify(const py::dict& source) const {
        const auto patch = placement_patch(source); CastingChart out;
        require_ok(modify_casting_chart(value_, patch, context_.compiled_tables(), &out), "CastingChart.modify");
        return std::unique_ptr<NativeCastingChart>(new NativeCastingChart(context_, std::move(out)));
    }
    std::unique_ptr<NativeCastingChart> shift(int32_t steps) const {
        CastingChart out;
        require_ok(shift_casting_life_palace(value_, steps, &out), "CastingChart.shift_life_palace");
        return std::unique_ptr<NativeCastingChart>(new NativeCastingChart(context_, std::move(out)));
    }
    std::unique_ptr<NativeCastingChart> reset() const {
        CastingChart out;
        require_ok(reset_casting_chart(value_, &out), "CastingChart.reset");
        return std::unique_ptr<NativeCastingChart>(new NativeCastingChart(context_, std::move(out)));
    }
private:
    ZiweiContext context_;
    CastingChart value_;
};
