#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "taiyin/bazi/bazi.h"
#include "taiyin/status.h"

#include <stdexcept>
#include <string>
#include <vector>

namespace py=pybind11;

namespace {

void require_ok(taiyin::Status status,const char* operation) {
    if(status!=taiyin::TAIYIN_STATUS_OK) {
        throw std::runtime_error(std::string(operation)+": "+taiyin::status_message(status));
    }
}

class BaziNativeContext {
public:
    BaziNativeContext(int earth_mode,int direction_mode,int qiyun_model,int dayun_model) {
        taiyin::bazi::BaziContextConfig config=taiyin::bazi::default_context_config();
        config.earth_palace_mode=earth_mode; config.qiyun_direction_mode=direction_mode;
        config.qiyun_time_model=qiyun_model; config.dayun_boundary_model=dayun_model;
        require_ok(taiyin::bazi::initialize_context(&context_,&config),"BaziContext initialization");
    }

    std::vector<uint8_t> kong_wang(uint8_t ganzhi) const {
        uint8_t values[2]; require_ok(taiyin::bazi::get_kong_wang(ganzhi,values),"Bazi.get_kong_wang");
        return std::vector<uint8_t>(values,values+2);
    }
    uint8_t ten_god(uint8_t day,uint8_t target) const {
        uint8_t out; require_ok(taiyin::bazi::get_ten_god(day,target,&out),"Bazi.get_ten_god"); return out;
    }
    std::vector<uint8_t> hidden_stems(uint8_t branch) const {
        uint8_t values[taiyin::bazi::kHiddenStemCapacity]; uint8_t count=0;
        require_ok(taiyin::bazi::get_hidden_stems(branch,values,&count),"Bazi.get_hidden_stems");
        return std::vector<uint8_t>(values,values+count);
    }
    py::dict stem_relation(uint8_t a,uint8_t b) const { return relation(a,b,false); }
    py::dict branch_relation(uint8_t a,uint8_t b) const { return relation(a,b,true); }
    py::dict triple_relation(uint8_t a,uint8_t b,uint8_t c) const {
        uint32_t flags=0; uint8_t combined=taiyin::bazi::kInvalidWuXing;
        require_ok(taiyin::bazi::calculate_branch_triple_relation(a,b,c,&flags,&combined),"Bazi.calc_branch_triple_relation");
        py::dict out; out["flags"]=flags; out["combined_element_id"]=combined; return out;
    }
    uint8_t life_stage(uint8_t stem,uint8_t branch,int mode) const {
        uint8_t out; require_ok(taiyin::bazi::get_life_stage(stem,branch,mode,&out),"Bazi.get_life_stage"); return out;
    }
    uint8_t flow_year(int year) const { uint8_t out; require_ok(taiyin::bazi::calculate_flow_year(year,&out),"Bazi.calc_liunian"); return out; }
    uint8_t flow_month(uint8_t year,uint8_t branch) const { uint8_t out; require_ok(taiyin::bazi::calculate_flow_month(year,branch,&out),"Bazi.calc_liuyue"); return out; }
    uint8_t flow_day(const taiyin::CalendarDateTime& date) const { uint8_t out; require_ok(taiyin::bazi::calculate_flow_day(date,&out),"Bazi.calc_liuri"); return out; }
    uint8_t flow_hour(uint8_t day,uint8_t hour) const { uint8_t out; require_ok(taiyin::bazi::calculate_flow_hour(day,hour,&out),"Bazi.calc_liushi"); return out; }
private:
    py::dict relation(uint8_t a,uint8_t b,bool branch) const {
        uint32_t flags=0; uint8_t combined=taiyin::bazi::kInvalidWuXing;
        require_ok(branch?taiyin::bazi::calculate_branch_relation(a,b,&flags,&combined)
                         :taiyin::bazi::calculate_stem_relation(a,b,&flags,&combined),
                   branch?"Bazi.calc_branch_relation":"Bazi.calc_stem_relation");
        py::dict out; out["flags"]=flags; out["combined_element_id"]=combined; return out;
    }
    taiyin::bazi::BaziContext context_;
};

}

PYBIND11_MODULE(_bazi_native,module) {
    module.doc()="Direct pybind11 bindings for the optional Taiyin BaZi extension";
    py::class_<BaziNativeContext>(module,"NativeBaziContext")
        .def(py::init<int,int,int,int>(),py::arg("earth_palace_mode")=0,
             py::arg("qiyun_direction_mode")=0,py::arg("qiyun_time_model")=0,
             py::arg("dayun_boundary_model")=0)
        .def("get_kong_wang",&BaziNativeContext::kong_wang)
        .def("get_ten_god",&BaziNativeContext::ten_god)
        .def("get_hidden_stems",&BaziNativeContext::hidden_stems)
        .def("calc_stem_relation",&BaziNativeContext::stem_relation)
        .def("calc_branch_relation",&BaziNativeContext::branch_relation)
        .def("calc_branch_triple_relation",&BaziNativeContext::triple_relation)
        .def("get_life_stage",&BaziNativeContext::life_stage)
        .def("calc_liunian",&BaziNativeContext::flow_year)
        .def("calc_liuyue",&BaziNativeContext::flow_month)
        .def("calc_liuri",&BaziNativeContext::flow_day)
        .def("calc_liushi",&BaziNativeContext::flow_hour);
}
