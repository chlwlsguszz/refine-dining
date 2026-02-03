package com.refinedining.domain.food.raw.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
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
public class RawFoodDataService {

    private final PublicDataClient publicDataClient;
    private final RawFoodMaterialRepository rawFoodMaterialRepository;

    /**
     * 공공데이터를 가져와서 DB에 동기화합니다.
     */
    @Transactional
    public void syncPublicFoodData(int page, int size) {
        PublicNutriResponse response = publicDataClient.fetchNutriData(page, size);

        if (response == null || response.response().body() == null) {
            log.warn("API 응답 데이터가 없습니다.");
            return;
        }

        List<PublicNutriResponse.NutriItem> items = response.response().body().items();

        for (PublicNutriResponse.NutriItem item : items) {
            saveOrUpdate(item);
        }

        log.info("성공적으로 {}건의 데이터를 동기화했습니다.", items.size());
    }

    private void saveOrUpdate(PublicNutriResponse.NutriItem item) {
        rawFoodMaterialRepository.findByFoodCd(item.foodCd())
                .ifPresentOrElse(
                        existingFood -> {
                            // 1. 새로운 데이터를 임시 엔티티로 변환
                            RawFoodMaterial updatedData = convertToEntity(item);
                            // 2. 기존 엔티티의 필드 업데이트 (Dirty Checking 발생)
                            existingFood.updateAllFields(updatedData);
                            log.debug("Existing data update: {}", item.foodNm());
                        },
                        () -> {
                            // 없으면 신규 생성
                            RawFoodMaterial newFood = convertToEntity(item);
                            rawFoodMaterialRepository.save(newFood);
                        }
                );
    }

    /**
     * DTO -> Entity 변환 (Service 계층 처리)
     */
    private RawFoodMaterial convertToEntity(PublicNutriResponse.NutriItem item) {
        return RawFoodMaterial.builder()
                .foodCd(item.foodCd())
                .foodNm(item.foodNm())
                .dataCd(item.dataCd())
                .typeNm(item.typeNm())
                .foodOriginCd(item.foodOriginCd())
                .foodOriginNm(item.foodOriginNm())
                .foodLv3Cd(item.foodLv3Cd())
                .foodLv3Nm(item.foodLv3Nm())
                .foodLv4Cd(item.foodLv4Cd())
                .foodLv4Nm(item.foodLv4Nm())
                .foodLv5Cd(item.foodLv5Cd())
                .foodLv5Nm(item.foodLv5Nm())
                .foodLv6Cd(item.foodLv6Cd())
                .foodLv6Nm(item.foodLv6Nm())
                .foodLv7Cd(item.foodLv7Cd())
                .foodLv7Nm(item.foodLv7Nm())
                .nutConSrtrQua(item.nutConSrtrQua())
                // 숫자형 파싱 처리
                .enerc(parseDouble(item.enerc()))
                .water(parseDouble(item.water()))
                .prot(parseDouble(item.prot()))
                .fatce(parseDouble(item.fatce()))
                .ash(parseDouble(item.ash()))
                .chocdf(parseDouble(item.chocdf()))
                .sugar(parseDouble(item.sugar()))
                .fibtg(parseDouble(item.fibtg()))
                .ca(parseDouble(item.ca()))
                .fe(parseDouble(item.fe()))
                .p(parseDouble(item.p()))
                .k(parseDouble(item.k()))
                .nat(parseDouble(item.nat()))
                .vitaRae(parseDouble(item.vitaRae()))
                .retol(parseDouble(item.retol()))
                .cartb(parseDouble(item.cartb()))
                .thia(parseDouble(item.thia()))
                .ribf(parseDouble(item.ribf()))
                .nia(parseDouble(item.nia()))
                .vitc(parseDouble(item.vitc()))
                .vitd(parseDouble(item.vitd()))
                .chole(parseDouble(item.chole()))
                .fasat(parseDouble(item.fasat()))
                .fatrn(parseDouble(item.fatrn()))
                // 메타데이터
                .refuse(item.refuse())
                .srcCd(item.srcCd())
                .srcNm(item.srcNm())
                .cooCd(item.cooCd())
                .cooNm(item.cooNm())
                .foodCooRgnNm(item.foodCooRgnNm())
                .imptYn(item.imptYn())
                .dataProdCd(item.dataProdCd())
                .dataProdNm(item.dataProdNm())
                .crtYmd(item.crtYmd())
                .prdCollCapMon(item.prdCollCapMon())
                .crtrYmd(item.crtrYmd())
                .insttCode(item.insttCode())
                .insttNm(item.insttNm())
                .build();
    }

    /**
     * 공공데이터의 특수문자("-", "N/A") 및 null 대응 파싱
     */
    private Double parseDouble(String value) {
        if (value == null || value.isBlank() || value.equals("-") || value.equalsIgnoreCase("N/A")) {
            return 0.0;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            log.warn("숫자 변환 실패: {}", value);
            return 0.0;
        }
    }

    @Transactional
    public void syncAllPublicFoodData() {
        int pageSize = 100;

        // 1. 최초 호출로 전체 데이터 개수(totalCount) 파악
        PublicNutriResponse initialResponse = publicDataClient.fetchNutriData(1, 1);
        if (initialResponse == null || initialResponse.response().body() == null) {
            throw new RuntimeException("공공데이터 API로부터 데이터를 가져올 수 없습니다.");
        }

        int totalCount = initialResponse.response().body().totalCount();
        int totalPages = (int) Math.ceil((double) totalCount / pageSize);

        log.info("전체 데이터 동기화 시작: 총 {}건, {}페이지", totalCount, totalPages);

        // 2. 페이지별로 루프를 돌며 저장
        for (int i = 1; i <= totalPages; i++) {
            try {
                syncPublicFoodData(i, pageSize);
                log.info("페이지 동기화 완료: {}/{}", i, totalPages);
            } catch (Exception e) {
                log.error("{} 페이지 동기화 중 오류 발생: {}", i, e.getMessage());
                // 특정 페이지 실패 시 건너뛸지, 전체 중단할지 결정 (여기서는 계속 진행)
                continue;
            }
        }

        log.info("모든 데이터 동기화가 완료되었습니다.");
    }
}