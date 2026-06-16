import { Injectable } from '@nestjs/common';

/**
 * PHI (Protected Health Information) Filter Service
 * Implements de-identification rules for HIPAA compliance
 */
@Injectable()
export class PHIFilterService {
  // Regex patterns for common PHI identifiers
  private readonly patterns = {
    // Phone numbers: (123) 456-7890, 123-456-7890, 1234567890
    phone: /(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g,
    
    // Email addresses
    email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    
    // Social Security Numbers: 123-45-6789, 123 45 6789
    ssn: /\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b/g,
    
    // Medical Record Numbers (MRN): MRN followed by digits
    mrn: /\b(MRN|mrn|M\.?R\.?N\.?)\s*:?\s*\d+/gi,
    
    // Dates in various formats (MM/DD/YYYY, YYYY-MM-DD, etc.)
    date: /\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b/g,
    
    // Street addresses (simplified pattern)
    address: /\b\d+\s+[A-Za-z0-9\s,.'#-]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\b/gi,
    
    // ZIP codes: 12345 or 12345-6789
    zipCode: /\b\d{5}(-\d{4})?\b/g,
  };

  /**
   * Anonymize text by replacing PHI with placeholders
   */
  anonymize(text: string): string {
    if (!text) return text;

    let anonymized = text;

    // Replace phone numbers
    anonymized = anonymized.replace(this.patterns.phone, '[PHONE]');

    // Replace emails
    anonymized = anonymized.replace(this.patterns.email, '[EMAIL]');

    // Replace SSNs
    anonymized = anonymized.replace(this.patterns.ssn, '[SSN]');

    // Replace MRNs
    anonymized = anonymized.replace(this.patterns.mrn, '[MRN]');

    // Replace dates
    anonymized = anonymized.replace(this.patterns.date, '[DATE]');

    // Replace addresses
    anonymized = anonymized.replace(this.patterns.address, '[ADDRESS]');

    // Replace ZIP codes
    anonymized = anonymized.replace(this.patterns.zipCode, '[ZIP]');

    return anonymized;
  }

  /**
   * Check if text contains potential PHI
   */
  containsPHI(text: string): boolean {
    if (!text) return false;

    return Object.values(this.patterns).some((pattern) => pattern.test(text));
  }

  /**
   * Redact specific patient identifiers from clinical notes
   */
  redactPatientIdentifiers(text: string, patientName?: string): string {
    let redacted = this.anonymize(text);

    // If patient name is provided, redact it
    if (patientName) {
      const namePattern = new RegExp(patientName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      redacted = redacted.replace(namePattern, '[PATIENT_NAME]');
    }

    return redacted;
  }

  /**
   * Sanitize metadata by removing PHI fields
   */
  sanitizeMetadata(metadata: Record<string, any>): Record<string, any> {
    const sensitiveKeys = [
      'patient_name',
      'dob',
      'ssn',
      'phone',
      'email',
      'address',
      'mrn',
      'driver_license',
    ];

    const sanitized = { ...metadata };

    sensitiveKeys.forEach((key) => {
      if (key in sanitized) {
        delete sanitized[key];
      }
    });

    return sanitized;
  }
}