package com.refinedining.domain.food.service;

import com.refinedining.domain.food.entity.FoodMaterial;
import com.refinedining.domain.food.repository.FoodMaterialRepository;
import com.refinedining.infra.publicdata.PublicDataClient;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class FoodDataService {

    private final PublicDataClient publicDataClient;
    private final FoodMaterialRepository foodMaterialRepository;

    @Transactional
    public void syncFoodData(int page, int size) {
        PublicNutriResponse response = publicDataClient.fetchNutriData(page, size);

        if (response == null || response.response().body() == null) {
            log.warn("공공데이터 응답이 비어있습니다.");
            return;
        }

        List<PublicNutriResponse.NutriItem> items = response.response().body().items();

        for (PublicNutriResponse.NutriItem item : items) {
            saveOrUpdate(item);
        }

        log.info("{}건의 식품 데이터 동기화 완료", items.size());
    }

    private void saveOrUpdate(PublicNutriResponse.NutriItem item) {
        // 이미 존재하는 식품이면 업데이트, 없으면 신규 생성 (Upsert 로직)
        FoodMaterial foodMaterial = foodMaterialRepository.findByFoodCd(item.foodCd())
                .orElseGet(() -> FoodMaterial.builder().foodCd(item.foodCd()).build());

        // 데이터 매핑 및 수치 변환
        FoodMaterial updatedMaterial = FoodMaterial.builder()
                .id(foodMaterial.getId()) // 기존 ID 유지 (업데이트 시 필요)
                .foodCd(item.foodCd())
                .foodNm(item.foodNm())
                .foodLv3Nm(item.foodLv3Nm())
                .nutConSrtrQua(item.nutConSrtrQua())
                .enerc(parseDecimal(item.enerc()))
                .prot(parseDecimal(item.prot()))
                .fatce(parseDecimal(item.fatce()))
                .chocdf(parseDecimal(item.chocdf()))
                .sugar(parseDecimal(item.sugar()))
                .nat(parseDecimal(item.nat()))
                .srcNm(item.srcNm())
                .crtrYmd(item.crtrYmd())
                .build();

        foodMaterialRepository.save(updatedMaterial);
    }

    // API에서 넘어오는 문자열 수치를 Double로 안전하게 변환
    private Double parseDecimal(String value) {
        if (value == null || value.isBlank() || value.equals("-")) {
            return 0.0;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            log.warn("수치 변환 실패: {}", value);
            return 0.0;
        }
    }
}