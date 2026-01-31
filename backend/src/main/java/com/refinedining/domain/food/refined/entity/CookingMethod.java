package com.refinedining.domain.food.refined.entity;

import lombok.Getter;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

@Getter
public enum CookingMethod {
    RAW("01", "생것", true),
    BOILED("46", "삶은것", false),
    BLANCHED("47", "데친것", false),
    STEAMED("49", "찐것", false),
    ROASTED("50", "구운것", false, Arrays.asList("51", "52", "53")), // 통합 처리
    FRIED("54", "튀긴것", false, Arrays.asList("55", "56")),        // 통합 처리
    STIR_FRIED("58", "볶은것", false),
    BRAISED("60", "조린것", false),
    MICROWAVED("64", "전자레인지로 가열한것", false);

    private final String code;
    private final String description;
    private final boolean isMasterCandidate;
    private final List<String> integratedCodes; // 통합될 하위 코드들

    CookingMethod(String code, String description, boolean isMasterCandidate) {
        this(code, description, isMasterCandidate, Collections.emptyList());
    }

    CookingMethod(String code, String description, boolean isMasterCandidate, List<String> integratedCodes) {
        this.code = code;
        this.description = description;
        this.isMasterCandidate = isMasterCandidate;
        this.integratedCodes = integratedCodes;
    }

    public static CookingMethod findByCode(String code) {
        return Arrays.stream(values())
                .filter(m -> m.code.equals(code) || m.integratedCodes.contains(code))
                .findFirst()
                .orElse(null);
    }
}