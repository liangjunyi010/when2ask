"""Dev-only health accounting: HTTP-200 schema errors are not API outages.

Every attempt and repair still debits the original persistent ledger. Actual
network/authentication errors keep the unchanged backend circuit-breaker policy.
"""
class SchemaAwareSession:
    def __init__(self,ledger,audit):self.ledger,self.audit=ledger,audit
    def reserve(self,backend):return self.ledger.reserve(backend)
    def outcome(self,backend,success,permanent_reason=None):
        record=self.audit.records[-1]
        schema_response=record.get('status')=='schema_error' and record.get('http_status')==200
        if schema_response:
            record['backend_health']='http_ok_schema_error';self.audit.flush()
        return self.ledger.outcome(backend,success or schema_response,permanent_reason)
