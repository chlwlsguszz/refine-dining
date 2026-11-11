package com.refinedining.domain.food.raw.service;

import com.refinedining.domain.food.raw.entity.RawFoodMaterial;
import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.infra.publicdata.PublicDataClient;
import com.refinedining.infra.publicdata.dto.PublicNutriResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RawFoodDataService {

    private final PublicDataClient publicDataClient;
    private final RawFoodMaterialRepository rawFoodMaterialRepository;
    private final TransactionTemplate transactionTemplate;

    /**
     * 공공데이터를 가져와서 DB에 동기화합니다.
     * 외부 API 호출은 트랜잭션 밖에서 수행하고, DB 반영만 트랜잭션 안에서 일괄 처리합니다.
     */
    public void syncPublicFoodData(int page, int size) {
        PublicNutriResponse response = publicDataClient.fetchNutriData(page, size);

        if (response == null || response.response() == null || response.response().body() == null) {
            log.warn("API 응답 데이터가 없습니다. (page={})", page);
            return;
        }

        List<PublicNutriResponse.NutriItem> items = response.response().body().items();
        if (items == null || items.isEmpty()) {
            log.info("동기화할 항목이 없습니다. (page={})", page);
            return;
        }

        if (transactionTemplate != null) {
            transactionTemplate.executeWithoutResult(status -> saveOrUpdateBatch(items));
        } else {
            saveOrUpdateBatch(items);
        }

        log.info("성공적으로 {}건의 데이터를 동기화했습니다. (page={})", items.size(), page);
    }

    @Transactional
    protected void saveOrUpdateBatch(List<PublicNutriResponse.NutriItem> items) {
        List<String> foodCds = items.stream()
                .map(PublicNutriResponse.NutriItem::foodCd)
                .filter(cd -> cd != null && !cd.isBlank())
                .distinct()
                .toList();

        Map<String, RawFoodMaterial> existingMap = rawFoodMaterialRepository.findAllByFoodCdIn(foodCds).stream()
                .collect(Collectors.toMap(RawFoodMaterial::getFoodCd, Function.identity(), (a, b) -> a));

        List<RawFoodMaterial> newEntities = new ArrayList<>();

        for (PublicNutriResponse.NutriItem item : items) {
            if (item.foodCd() == null || item.foodCd().isBlank()) {
                continue;
            }
            RawFoodMaterial converted = convertToEntity(item);
            RawFoodMaterial existing = existingMap.get(item.foodCd());
            if (existing != null) {
                existing.updateAllFields(converted);
            } else {
                newEntities.add(converted);
                existingMap.put(item.foodCd(), converted);
            }
        }

        if (!newEntities.isEmpty()) {
            rawFoodMaterialRepository.saveAll(newEntities);
        }
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
    static Double parseDouble(String value) {
        if (value == null || value.isBlank() || value.equals("-") || value.equalsIgnoreCase("N/A")) {
            return null;
        }
        try {
            double parsed = Double.parseDouble(value);
            return Double.isFinite(parsed) ? parsed : null;
        } catch (NumberFormatException e) {
            log.warn("숫자 변환 실패: {}", value);
            return null;
        }
    }

    public void syncAllPublicFoodData() {
        int pageSize = 100;

        // 1. 최초 호출로 전체 데이터 개수(totalCount) 파악
        PublicNutriResponse initialResponse = publicDataClient.fetchNutriData(1, 1);
        if (initialResponse == null || initialResponse.response() == null || initialResponse.response().body() == null) {
            throw new IllegalStateException("공공데이터 API로부터 데이터를 가져올 수 없습니다.");
        }

        int totalCount = initialResponse.response().body().totalCount();
        int totalPages = (int) Math.ceil((double) totalCount / pageSize);

        log.info("전체 데이터 동기화 시작: 총 {}건, {}페이지", totalCount, totalPages);

        List<Integer> failedPages = new ArrayList<>();

        // 2. 페이지별로 루프를 돌며 저장 (각 페이지별 독립 트랜잭션)
        for (int i = 1; i <= totalPages; i++) {
            try {
                syncPublicFoodData(i, pageSize);
                log.info("페이지 동기화 완료: {}/{}", i, totalPages);
            } catch (Exception e) {
                log.error("{} 페이지 동기화 중 오류 발생: {}", i, e.getMessage());
                failedPages.add(i);
            }
        }

        log.info("모든 데이터 동기화가 완료되었습니다. (실패 페이지 수: {})", failedPages.size());
    }
}
