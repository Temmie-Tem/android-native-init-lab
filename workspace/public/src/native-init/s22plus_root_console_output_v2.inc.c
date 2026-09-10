/* Included after rc1_state/framing helpers. Output credit is consumed by this
 * sole PID1 owner; pipe deferral must not bypass exec/reap/deadline/CONTROL.
 */
static long rc1_output_tick(struct rc1_state *s) {
    unsigned first=s->output_turn;
    for(unsigned slot=0;slot<2U;slot++) {
        unsigned i=(first+slot)&1U;
        if(s->pipe[i]<0)continue;
        /* Do not read bytes that cannot be queued. Exhausted byte/frame
         * budgets retain the existing bounded discard/accounting path. */
        if(s->qcount>=RC1_QUEUE-3U && s->total<RC1_OUTPUT_LIMIT &&
           s->ordinal<RC1_OUTPUT_FRAME_LIMIT)continue;
        uint8_t body[780];long n=sys_read(s->pipe[i],body+12,768U);
        if(n>0) {
            if(s->total+(unsigned)n>RC1_OUTPUT_LIMIT || s->ordinal>=RC1_OUTPUT_FRAME_LIMIT) {
                s->flags|=RC1_FLAG_TRUNCATED;
                if(s->dropped<=0xffffffffU-(unsigned)n)s->dropped+=(unsigned)n;
                else s->dropped=0xffffffffU;
            } else {
                p328_store_le32(body,s->id);p328_store_le32(body+4,++s->ordinal);
                p328_store_le32(body+8,i+1U);
                long rc=rc1_queue(s,RC1_OUTPUT,s->id,body,(unsigned)n+12U);
                if(rc)return rc;
                s->total+=(unsigned)n;s->output_turn=(i+1U)&1U;
            }
        } else if(!n){(void)sys_close(s->pipe[i]);s->pipe[i]=-1;}
        else if(n!=-EAGAIN && n!=-P260_EINTR)return n;
    }
    return 0;
}
