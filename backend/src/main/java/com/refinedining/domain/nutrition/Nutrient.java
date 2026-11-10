package com.refinedining.domain.nutrition;

enum Nutrient {
    enerc("에너지","kcal"), water("수분","g"), prot("단백질","g"), fatce("지방","g"), ash("회분","g"),
    chocdf("탄수화물","g"), sugar("당류","g"), fibtg("식이섬유","g"), ca("칼슘","mg"), fe("철","mg"),
    p("인","mg"), k("칼륨","mg"), nat("나트륨","mg"), vita_rae("비타민 A","μg RAE"), retol("레티놀","μg"),
    cartb("베타카로틴","μg"), thia("티아민","mg"), ribf("리보플라빈","mg"), nia("니아신","mg"), vitc("비타민 C","mg"),
    vitd("비타민 D","μg"), chole("콜레스테롤","mg"), fasat("포화지방산","g"), fatrn("트랜스지방산","g");

    final String label;
    final String unit;
    Nutrient(String label, String unit) { this.label = label; this.unit = unit; }
}
