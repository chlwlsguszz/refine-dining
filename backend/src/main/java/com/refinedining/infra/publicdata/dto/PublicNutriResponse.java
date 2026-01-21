package com.refinedining.infra.publicdata.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record PublicNutriResponse(Response response) {
    public record Response(Header header, Body body) {}
    public record Header(String resultCode, String resultMsg) {}
    public record Body(List<NutriItem> items, int totalCount) {}

    public record NutriItem(
            @JsonProperty("foodCd") String foodCd,
            @JsonProperty("foodNm") String foodNm,
            @JsonProperty("foodLv3Nm") String foodLv3Nm,
            @JsonProperty("nutConSrtrQua") String nutConSrtrQua,
            @JsonProperty("enerc") String enerc,
            @JsonProperty("prot") String prot,
            @JsonProperty("fatce") String fatce,
            @JsonProperty("chocdf") String chocdf,
            @JsonProperty("sugar") String sugar,
            @JsonProperty("nat") String nat,
            @JsonProperty("srcNm") String srcNm,
            @JsonProperty("crtrYmd") String crtrYmd
    ) {}
}