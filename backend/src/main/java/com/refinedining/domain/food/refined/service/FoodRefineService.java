package com.refinedining.domain.food.refined.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.domain.food.refined.entity.FoodMaterial;
import com.refinedining.domain.food.refined.entity.CookingMethod;
import com.refinedining.domain.food.refined.repository.FoodMaterialRepository;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FoodRefineService {

    private final RawFoodMaterialRepository rawFoodRepository;
    private final FoodMaterialRepository foodMaterialRepository;

    @PersistenceContext
    private EntityManager em;

    @Transactional
    public void refineAll() {

        // 기존 정제 데이터 초기화 (필요시)
        em.createNativeQuery("SET FOREIGN_KEY_CHECKS = 0").executeUpdate();
        em.createNativeQuery("TRUNCATE TABLE food_materials").executeUpdate();
        em.createNativeQuery("SET FOREIGN_KEY_CHECKS = 1").executeUpdate();
        log.info("기존 정제 데이터를 모두 삭제하고 ID 카운터를 초기화했습니다.");

        List<RawFoodMaterial> allRaw = rawFoodRepository.findAll();

        // 1. 수산물 및 기초 필터링
        List<RawFoodMaterial> filteredRaw = allRaw.stream()
                .filter(this::isValidRawData)
                .collect(Collectors.toList());

        // 2. 소분류 코드(foodLv6Cd)로 그룹핑
        Map<String, List<RawFoodMaterial>> groupedByLv6 = filteredRaw.stream()
                .collect(Collectors.groupingBy(RawFoodMaterial::getFoodLv6Cd));

        log.info("정제 프로세스 시작: 총 {}개의 잠재적 그룹 확인", groupedByLv6.size());

        // 3. 그룹별 처리 및 저장
        for (Map.Entry<String, List<RawFoodMaterial>> entry : groupedByLv6.entrySet()) {
            processAndSaveGroup(entry.getValue());
        }
    }

    private boolean isValidRawData(RawFoodMaterial raw) {
        if ("2".equals(raw.getSrcCd())) {
            return raw.getFoodNm().contains("대표") && raw.getFoodNm().contains("평균");
        }
        return true;
    }

    /**
     * 그룹 데이터를 분석하여 부모-자식 관계를 형성하고,
     * 유효한 데이터셋(자식이 있는 부모)인 경우에만 DB에 저장합니다.
     */
    private void processAndSaveGroup(List<RawFoodMaterial> groupItems) {
        // [01] 생것(Parent) 찾기
        RawFoodMaterial parentRaw = groupItems.stream()
                .filter(raw -> "01".equals(raw.getFoodLv7Cd()))
                .findFirst()
                .orElse(null);

        if (parentRaw == null) return;

        // 유효한 가공 방식(Enum 매핑 성공)을 가진 자식들만 추출
        List<FoodMaterial> childEntities = groupItems.stream()
                .filter(raw -> !"01".equals(raw.getFoodLv7Cd()))
                .filter(raw -> CookingMethod.findByCode(raw.getFoodLv7Cd()) != null)
                .map(raw -> convertToEntity(raw))
                .collect(Collectors.toList());

        // 로직 변경: 자식이 하나도 없으면 부모도 저장하지 않고 종료
        if (childEntities.isEmpty()) {
            return;
        }

        // 자식이 존재할 때만 부모 엔티티 생성 및 저장 프로세스 진행
        FoodMaterial parentEntity = convertToEntity(parentRaw);

        for (FoodMaterial child : childEntities) {
            parentEntity.addChild(child);
        }

        foodMaterialRepository.save(parentEntity);
    }

    private FoodMaterial convertToEntity(RawFoodMaterial raw) {
        CookingMethod method = CookingMethod.findByCode(raw.getFoodLv7Cd());

        return FoodMaterial.builder()
                .foodCd(raw.getFoodCd())
                .name(raw.getFoodNm())
                .foodLv6Cd(raw.getFoodLv6Cd())
                .foodLv7Cd(method != null ? method.getCode() : raw.getFoodLv7Cd())
                .cookingMethod(method != null ? method.getDescription() : "기타")
                .calories(raw.getEnerc())
                .protein(raw.getProt())
                .fat(raw.getFatce())
                .carbohydrate(raw.getChocdf())
                .sugar(raw.getSugar())
                .sodium(raw.getNat())
                .build();
    }
}