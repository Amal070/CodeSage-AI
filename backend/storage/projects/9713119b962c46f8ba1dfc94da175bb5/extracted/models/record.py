from pydantic import BaseModel, Field

class DataRecord(BaseModel):
    id: int
    value: float = Field(gt=0)
    category: str = 'general'
    status: str = 'pending'

    def calculate_tax(self, tax_rate: float = 0.18) -> float:
        """Calculates regional tax on the record value."""
        return round(self.value * tax_rate, 2)
