// SPDX-License-Identifier: GPL-2.0-only
/* Unmodified tcs_cmd_gen/tcs_list_gen from the retained Linux bcm-voter.c.
 * Source excerpt SHA256: 22aa96ae57c67d69d5c49781848fe4e5b62fb499a2234a68b0d5234ac1b17a52
 */
static inline void tcs_cmd_gen(struct tcs_cmd *cmd, u64 vote_x, u64 vote_y,
			       u32 addr, bool commit, bool wait)
{
	bool valid = true;

	if (!cmd)
		return;

	memset(cmd, 0, sizeof(*cmd));

	if (vote_x == 0 && vote_y == 0)
		valid = false;

	if (vote_x > BCM_TCS_CMD_VOTE_MASK)
		vote_x = BCM_TCS_CMD_VOTE_MASK;

	if (vote_y > BCM_TCS_CMD_VOTE_MASK)
		vote_y = BCM_TCS_CMD_VOTE_MASK;

	cmd->addr = addr;
	cmd->data = BCM_TCS_CMD(commit, valid, vote_x, vote_y);

	/*
	 * Set the wait for completion flag on command that need to be completed
	 * before the next command.
	 */
	cmd->wait = wait;
}

static void tcs_list_gen(struct bcm_voter *voter, int bucket,
			 struct tcs_cmd tcs_list[MAX_VCD],
			 int n[MAX_VCD + 1])
{
	struct list_head *bcm_list = &voter->commit_list;
	struct qcom_icc_bcm *bcm;
	bool commit, wait;
	size_t idx = 0, batch = 0, cur_vcd_size = 0;

	memset(n, 0, sizeof(int) * (MAX_VCD + 1));

	list_for_each_entry(bcm, bcm_list, list) {
		commit = false;
		cur_vcd_size++;
		if ((list_is_last(&bcm->list, bcm_list)) ||
		    bcm->aux_data.vcd != list_next_entry(bcm, list)->aux_data.vcd) {
			commit = true;
			cur_vcd_size = 0;
		}

		wait = commit && (voter->tcs_wait & BIT(bucket));

		tcs_cmd_gen(&tcs_list[idx], bcm->vote_x[bucket],
			    bcm->vote_y[bucket], bcm->addr, commit, wait);
		idx++;
		n[batch]++;
		/*
		 * Batch the BCMs in such a way that we do not split them in
		 * multiple payloads when they are under the same VCD. This is
		 * to ensure that every BCM is committed since we only set the
		 * commit bit on the last BCM request of every VCD.
		 */
		if (n[batch] >= MAX_RPMH_PAYLOAD) {
			if (!commit) {
				n[batch] -= cur_vcd_size;
				n[batch + 1] = cur_vcd_size;
			}
			batch++;
		}
	}
}
