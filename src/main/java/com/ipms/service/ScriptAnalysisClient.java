package com.ipms.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;

import java.io.File;

@Service
public class ScriptAnalysisClient {

    private final RestTemplate restTemplate;

    // Change the URL to the PDF analysis endpoint
    @Value("${analysis.service.pdf.url:http://localhost:8000/analyze-script-pdf}")
    private String analysisApiUrl;

    public ScriptAnalysisClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * Calls the external FastAPI service by sending the PDF file as multipart/form-data.
     * @param pdfFilePath The absolute or relative path to the stored PDF file.
     * @return The raw JSON response from the analysis service as a String.
     */
    public String analyzeScriptPdf(String pdfFilePath) {
        // 1. Prepare the file resource
        File pdfFile = new File(pdfFilePath);
        if (!pdfFile.exists()) {
            System.err.println("PDF file not found at path: " + pdfFilePath);
            return null; 
        }
        Resource fileResource = new FileSystemResource(pdfFile);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        
        body.add("file", fileResource); 

        HttpHeaders headers = new HttpHeaders();
        
        headers.setContentType(MediaType.MULTIPART_FORM_DATA); 

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        try {
            System.out.println("Calling FastAPI analysis service with PDF: " + pdfFilePath);
            return restTemplate.postForObject(analysisApiUrl, requestEntity, String.class);
        } catch (Exception e) {
            System.err.println("Error calling script analysis service: " + e.getMessage());
            return null;
        }
    }
}