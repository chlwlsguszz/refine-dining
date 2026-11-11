package com.refinedining.domain.food.refined.service;

import com.refinedining.domain.food.refined.dto.FoodCompareResponse;
import com.refinedining.domain.food.refined.dto.FoodSearchResponse;
import com.refinedining.domain.food.refined.entity.FoodMaterial;
import com.refinedining.domain.food.refined.repository.FoodMaterialRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.NoSuchElementException;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FoodSearchService {
    private final FoodMaterialRepository foodMaterialRepository;

    @Transactional(readOnly = true)
    public List<FoodSearchResponse> searchFood(String name, int page, int size) {
        String keyword = name != null ? name.trim() : "";
        int safePage = Math.max(0, page);
        int safeSize = Math.min(Math.max(1, size), 100);
        Pageable pageable = PageRequest.of(safePage, safeSize);
        return foodMaterialRepository.findByNameWithChildren(keyword, pageable).stream()
                .map(FoodSearchResponse::from)
                .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public FoodCompareResponse getCompareData(Long childId) {
        FoodMaterial child = foodMaterialRepository.findChildWithParentById(childId)
                .orElseThrow(() -> new NoSuchElementException("해당 조리 식품 정보를 찾을 수 없습니다. (id=" + childId + ")"));
        return FoodCompareResponse.of(child.getParent(), child);
    }
}
