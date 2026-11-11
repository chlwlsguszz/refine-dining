package com.refinedining.domain.food.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.domain.food.refined.dto.FoodRefineReport;
import com.refinedining.domain.food.refined.dto.FoodRefineReport.ExclusionReason;
import com.refinedining.domain.food.refined.dto.FoodSearchResponse;
import com.refinedining.domain.food.refined.entity.FoodMaterial;
import com.refinedining.domain.food.refined.repository.FoodMaterialRepository;
import com.refinedining.domain.food.refined.service.FoodRefineService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

@ExtendWith(MockitoExtension.class)
class FoodRefineServiceTest {

    @Mock
    private RawFoodMaterialRepository rawFoodRepository;

    @Mock
    private FoodMaterialRepository foodMaterialRepository;

    @InjectMocks
    private FoodRefineService foodRefineService;

    @Test
    @DisplayName("소분류(foodLv6Cd) 기준으로 생것(01) 부모와 유효한 조리법 자식을 계층화하여 저장한다.")
    @SuppressWarnings("unchecked")
    void refineAll_GroupsParentAndChildrenCorrectly() {
        // given
        RawFoodMaterial rawParent = RawFoodMaterial.builder()
                .foodCd("F001")
                .foodNm("돼지고기, 삼겹살, 생것")
                .foodLv6Cd("LV6_PORK_BELLY")
                .foodLv7Cd("01")
                .srcCd("1")
                .enerc(330.0)
                .prot(17.0)
                .fatce(28.0)
                .chocdf(0.0)
                .sugar(0.0)
                .nat(50.0)
                .build();

        // 51은 CookingMethod.ROASTED("50", "구운것", integratedCodes=["51","52","53"])로 통합되어야 함
        RawFoodMaterial roastedChild = RawFoodMaterial.builder()
                .foodCd("F002")
                .foodNm("돼지고기, 삼겹살, 팬에 구운것")
                .foodLv6Cd("LV6_PORK_BELLY")
                .foodLv7Cd("51")
                .srcCd("1")
                .enerc(450.0)
                .prot(24.0)
                .fatce(38.0)
                .chocdf(0.0)
                .sugar(0.0)
                .nat(70.0)
                .build();

        // 자식이 없는 단독 그룹 -> 저장되지 않아야 함
        RawFoodMaterial orphanParent = RawFoodMaterial.builder()
                .foodCd("F003")
                .foodNm("사과, 생것")
                .foodLv6Cd("LV6_APPLE")
                .foodLv7Cd("01")
                .srcCd("1")
                .enerc(52.0)
                .build();

        given(rawFoodRepository.findAll()).willReturn(List.of(rawParent, roastedChild, orphanParent));

        // when
        foodRefineService.refineAll();

        // then
        ArgumentCaptor<List<FoodMaterial>> captor = ArgumentCaptor.forClass(List.class);
        verify(foodMaterialRepository).saveAll(captor.capture());

        List<FoodMaterial> savedParents = captor.getValue();
        assertThat(savedParents).hasSize(1);

        FoodMaterial savedParent = savedParents.get(0);
        assertThat(savedParent.getFoodCd()).isEqualTo("F001");
        assertThat(savedParent.getCookingMethod()).isEqualTo("생것");
        assertThat(savedParent.getChildren()).hasSize(1);

        FoodMaterial savedChild = savedParent.getChildren().get(0);
        assertThat(savedChild.getFoodCd()).isEqualTo("F002");
        assertThat(savedChild.getFoodLv7Cd()).isEqualTo("50");
        assertThat(savedChild.getCookingMethod()).isEqualTo("구운것");

        // FoodSearchResponse DTO 매핑 검증 (foodCd가 cookingMethod가 아닌 실제 foodCd로 매핑되는지 확인)
        FoodSearchResponse dto = FoodSearchResponse.from(savedParent);
        assertThat(dto.foodCd()).isEqualTo("F001");
        assertThat(dto.cookingMethods()).hasSize(1);
        assertThat(dto.cookingMethods().get(0).foodCd()).isEqualTo("F002");
    }

    @Test
    @DisplayName("필터가 겹치는 원본도 최초 제외 사유에 한 번만 집계하고, 미등록 조리코드별 빈도를 구한다.")
    void analyzeRefinement_AccountsForEveryRowOnce() {
        List<RawFoodMaterial> rows = List.of(
                rawFood("missing-name", null, null, null, "2"),
                rawFood("seafood", "", "01", "대표 고등어", "2"),
                rawFood("missing-group", " ", "46"),
                rawFood("no-parent-boiled", "orphan", "46"),
                rawFood("no-parent-unknown", "orphan", "48"),
                rawFood("no-parent-missing", "orphan", null),
                rawFood("parent", "paired", "01", "고등어 대표 평균", "2"),
                rawFood("extra-parent", "paired", "01"),
                rawFood("grilled", "paired", "51"),
                rawFood("missing-method", "paired", null),
                rawFood("blank-method", "paired", " "),
                rawFood("unknown-1", "paired", "48"),
                rawFood("unknown-2", "paired", "48"),
                rawFood("unknown-3", "paired", "48"),
                rawFood("unpaired-parent", "unpaired", "01"),
                rawFood("unknown-4", "unpaired", "03"));
        given(rawFoodRepository.findAll()).willReturn(rows);

        FoodRefineReport report = foodRefineService.analyzeRefinement();

        verifyNoInteractions(foodMaterialRepository);
        Map<ExclusionReason, Long> expectedCounts = Map.of(
                ExclusionReason.MISSING_FOOD_NAME, 1L,
                ExclusionReason.SEAFOOD_NAME_FILTER, 1L,
                ExclusionReason.MISSING_LV6_CODE, 1L,
                ExclusionReason.NO_RAW_PARENT, 3L,
                ExclusionReason.ADDITIONAL_RAW_PARENT, 1L,
                ExclusionReason.MISSING_COOKING_CODE, 2L,
                ExclusionReason.UNMAPPED_COOKING_CODE, 4L,
                ExclusionReason.NO_SUPPORTED_CHILD, 1L);
        assertThat(report.exclusions().keySet()).isEqualTo(expectedCounts.keySet());
        expectedCounts.forEach((reason, count) ->
                assertThat(report.exclusions().get(reason).count()).as(reason.name()).isEqualTo(count));
        assertThat(report.exclusions().get(ExclusionReason.UNMAPPED_COOKING_CODE).examples()).hasSize(3);
        assertThat(report.unmappedCookingCodes()).isEqualTo(Map.of("48", 3L, "03", 1L));
        assertThat(report.retainedParents()).isEqualTo(1);
        assertThat(report.retainedChildren()).isEqualTo(1);
        assertThat(report.excludedRows()).isEqualTo(14);
        assertThat(report.totalRawRows()).isEqualTo(rows.size());
        assertThat(report.totalRawRows())
                .isEqualTo(report.retainedParents() + report.retainedChildren() + report.excludedRows());
    }

    @Test
    @DisplayName("빈 원본도 모든 제외 사유의 0건과 빈 표본을 보고한다.")
    void analyzeRefinement_ReportsZeroForEveryReasonOnEmptyInput() {
        given(rawFoodRepository.findAll()).willReturn(List.of());

        FoodRefineReport report = foodRefineService.analyzeRefinement();

        assertThat(report.totalRawRows()).isZero();
        assertThat(report.retainedParents()).isZero();
        assertThat(report.retainedChildren()).isZero();
        assertThat(report.excludedRows()).isZero();
        assertThat(report.unmappedCookingCodes()).isEmpty();
        assertThat(report.exclusions()).containsOnlyKeys(ExclusionReason.values());
        report.exclusions().values().forEach(stats -> {
            assertThat(stats.count()).isZero();
            assertThat(stats.examples()).isEmpty();
        });
        verifyNoInteractions(foodMaterialRepository);
    }

    @Test
    @DisplayName("진단에서 채택한 부모·자식 수가 동일한 원본으로 실제 정제한 결과와 일치한다.")
    @SuppressWarnings("unchecked")
    void analyzeRefinement_MatchesSavedHierarchy() {
        given(rawFoodRepository.findAll()).willReturn(List.of(
                rawFood("first", "group", "01"),
                rawFood("second", "group", "01"),
                rawFood("pan", "group", "51"),
                rawFood("oven", "group", "53"),
                rawFood("unmapped", "group", "48"),
                rawFood("standalone", "another-group", "01")));

        FoodRefineReport report = foodRefineService.analyzeRefinement();
        verifyNoInteractions(foodMaterialRepository);
        foodRefineService.refineAll();

        ArgumentCaptor<List<FoodMaterial>> captor = ArgumentCaptor.forClass(List.class);
        verify(foodMaterialRepository).saveAll(captor.capture());
        List<FoodMaterial> parents = captor.getValue();
        assertThat(parents).extracting(FoodMaterial::getFoodCd).containsExactly("first");
        List<FoodMaterial> children = parents.get(0).getChildren();
        assertThat(children).extracting(FoodMaterial::getFoodCd).containsExactlyInAnyOrder("pan", "oven");
        assertThat(report.retainedParents()).isEqualTo(parents.size());
        assertThat(report.retainedChildren()).isEqualTo(children.size());
    }

    private RawFoodMaterial rawFood(String foodCd, String group, String method) {
        return rawFood(foodCd, group, method, foodCd, "1");
    }

    private RawFoodMaterial rawFood(String foodCd, String group, String method, String name, String source) {
        return RawFoodMaterial.builder()
                .foodCd(foodCd).foodNm(name).srcCd(source)
                .foodLv6Cd(group).foodLv7Cd(method)
                .build();
    }
}
