package com.refinedining.domain.food.refined.service;

import com.refinedining.domain.food.raw.repository.RawFoodMaterialRepository;
import com.refinedining.domain.food.refined.dto.FoodSearchResponse;
import com.refinedining.domain.food.refined.repository.FoodMaterialRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class FoodSearchService {
    private final FoodMaterialRepository foodMaterialRepository;

    @Transactional(readOnly = true)
    public List<FoodSearchResponse> searchFood(String name, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        return foodMaterialRepository.findByNameWithChildren(name, pageable).stream()
                .map(FoodSearchResponse::from)
                .collect(Collectors.toList());
    }
}
