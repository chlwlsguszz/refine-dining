package com.refinedining.domain.food.refined.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.domain.food.refined.dto.FoodRefineReport;
import com.refinedining.domain.food.refined.entity.CookingMethod;
import com.refinedining.domain.food.refined.entity.FoodMaterial;
import com.refinedining.domain.food.refined.repository.FoodMaterialRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class FoodRefineService {

    private final RawFoodMaterialRepository rawFoodRepository;
    private final FoodMaterialRepository foodMaterialRepository;

    @Transactional(readOnly = true)
    public FoodRefineReport analyzeRefinement() {
        return FoodRefinementPlan.from(rawFoodRepository.findAll()).report();
    }

    @Transactional
    public void refineAll() {
        // TRUNCATE는 MySQL에서 암묵적 커밋(DDL)을 발생시켜 트랜잭션 롤백이 불가능하므로,
        // 자식 -> 부모 순서의 벌크 DELETE를 사용하여 원자성을 보장합니다.
        foodMaterialRepository.deleteAllChildrenInBatch();
        foodMaterialRepository.deleteAllParentsInBatch();
        log.info("기존 정제 데이터를 모두 정리했습니다.");

        FoodRefinementPlan plan = FoodRefinementPlan.from(rawFoodRepository.findAll());
        List<FoodMaterial> parents = plan.retainedGroups().stream().map(this::toParentEntity).toList();
        foodMaterialRepository.saveAll(parents);
        FoodRefineReport report = plan.report();
        log.info("정제 완료: 원본 {}행, 부모 {}행, 자식 {}행, 제외 {}행",
                report.totalRawRows(), report.retainedParents(), report.retainedChildren(), report.excludedRows());
    }

    private FoodMaterial toParentEntity(FoodRefinementPlan.RetainedGroup group) {
        FoodMaterial parent = convertToEntity(group.parent());
        for (RawFoodMaterial child : group.children()) {
            parent.addChild(convertToEntity(child));
        }
        return parent;
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
