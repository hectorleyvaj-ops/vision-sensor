from services.controller_protocol import (
    PROTOCOL_VERSION,
    decode_message,
    encode_message,
)


class ControllerSimulator:
    """Machine-neutral simulator of the vision controller protocol."""

    def __init__(self, boot_token="SIM00001"):
        self.boot_token = boot_token
        self.counter = 0
        self.synced = False
        self.vision_ready = False
        self.active_cycle = None
        self.model = None
        self.vision_result = None

    def receive(self, payload):
        message = decode_message(payload)
        fields = message.fields

        if message.kind == "HELLO":
            self.synced = fields.get("PROTO") == PROTOCOL_VERSION
            self.vision_ready = False
            return [
                encode_message(
                    "HELLO_ACK",
                    proto=PROTOCOL_VERSION,
                    fw="controller-simulator",
                    ready=int(self.synced),
                )
            ]

        if message.kind == "READY":
            requested = fields.get("STATE") == "1"
            self.vision_ready = self.synced and requested
            status = "OK" if self.vision_ready == requested else "REJECTED"
            return [encode_message("ACK", type="READY", status=status)]

        if message.kind == "VISION_RESULT":
            cycle = fields.get("CYCLE")
            if cycle != self.active_cycle:
                return [
                    encode_message(
                        "ACK",
                        type="VISION_RESULT",
                        cycle=cycle,
                        status="REJECTED",
                        error="STALE_CYCLE",
                    )
                ]
            self.vision_result = fields.get("RESULT")
            return [
                encode_message(
                    "ACK",
                    type="VISION_RESULT",
                    cycle=cycle,
                    status="OK",
                )
            ]

        return [encode_message("ERROR", code="UNKNOWN_MESSAGE")]

    def trigger(self, model):
        if not (self.synced and self.vision_ready):
            return encode_message("ERROR", code="NOT_READY")
        if self.active_cycle is not None:
            return encode_message("ERROR", code="CONTROLLER_BUSY")

        self.model = str(model)
        self.counter += 1
        self.active_cycle = f"{self.boot_token}-{self.counter}"
        self.vision_result = None
        return encode_message(
            "TRIGGER",
            cycle=self.active_cycle,
            model=self.model,
        )

    def final_result(self, result):
        if self.active_cycle is None:
            return encode_message("ERROR", code="NO_ACTIVE_CYCLE")
        return encode_message(
            "FINAL_RESULT",
            cycle=self.active_cycle,
            result=result,
        )

    def release_cycle(self):
        self.active_cycle = None
        self.vision_result = None

    def cancel(self, reason="EXTERNAL_CANCEL"):
        cycle = self.active_cycle
        self.release_cycle()
        return encode_message("CANCEL", cycle=cycle, reason=reason)
