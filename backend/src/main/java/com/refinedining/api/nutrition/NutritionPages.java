package com.refinedining.api.nutrition;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
@Profile("rag-demo")
public class NutritionPages {
    @GetMapping({"/nutrition", "/nutrition/review"})
    public String page() { return "forward:/index.html"; }
}
